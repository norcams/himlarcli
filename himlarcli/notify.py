import ConfigParser
import smtplib
from email.mime.text import MIMEText
from himlarcli import utils


class Notify(object):

    def __init__(self, config_path, debug=False, log=None):
        debug_level = 1 if debug else 0
        self.config_path = config_path
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        self.debug = debug
        self.dry_run = False
        self.ksclient = None
        self.server = smtplib.SMTP(self.get_config('mail', 'smtp'), 25)
        self.server.set_debuglevel(debug_level)
        self.server.starttls()

    def send_mail(self, toaddr, msg):
        from_addr = self.get_config('mail', 'from_addr')
        msg['From'] = from_addr
        msg['To'] = toaddr
        self.server.sendmail(from_addr, toaddr, msg.as_string())

    def close(self):
        self.server.quit()

    def set_dry_run(self, dry_run):
        self.dry_run = dry_run

    def set_keystone_client(self, ksclient):
        self.ksclient = ksclient

    def get_config(self, section, option):
        try:
            value = self.config.get(section, option)
            return value
        except ConfigParser.NoOptionError:
            self.logger.debug('=> config file section [%s] missing option %s'
                              % (section, option))
        except ConfigParser.NoSectionError:
            self.logger.debug('=> config file missing section %s' % section)
        return None

    def mail_instance_owner(self, instances, body, subject, admin=False):
        if not self.ksclient:
            self.logger.error('=> notify aborted: unable to find keystone client')
            return
        users = dict()
        for i in instances:
            if not admin:
                user = self.ksclient.get_user_by_id(i.user_id)
                email = self.__get_user_email(user)
            if admin or not email:
                project = self.ksclient.get_project_by_id(i.tenant_id)
                email = self.__get_project_email(project)
            if not email:
                self.logger.debug('=> unable to find owner of %s (%s)', i.name, i.id)
                continue
            if email not in users:
                users[email] = dict()
            users[email][i.name] = {'status': i.status}
        # Send mail
        for user, instances in users.iteritems():
            user_instances = ""
            for server, info in instances.iteritems():
                user_instances += "%s (current status %s)\n" % (server, info['status'])
            msg = MIMEText(user_instances + body, 'plain', 'utf-8')
            msg['Subject'] = subject
            log_msg = 'sending mail to %s' % user
            if not self.dry_run:
                self.send_mail(user, msg)
            else:
                log_msg = 'DRY-RUN: ' + log_msg
            self.logger.debug('=> %s', log_msg)

    @staticmethod
    def __get_user_email(user):
        if not user:
            return None
        if hasattr(user, 'mail'):
            return user.email.lower()
        if hasattr(user, 'name') and "@" in user.name:
            return user.name.lower()
        return None

    @staticmethod
    def __get_project_email(project):
        if not project:
            return None
        if hasattr(project, 'admin'):
            return project.admin.lower()
        if hasattr(project, 'type') and project.type == 'personal':
            if hasattr(project, 'name') and "@" in project.name:
                return project.name.lower()
        return None
