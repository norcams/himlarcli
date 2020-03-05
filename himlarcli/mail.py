from himlarcli.client import Client
import ConfigParser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class Mail(Client):

    def __init__(self, config_path, debug=False, log=None):
        super(Mail, self).__init__(config_path, debug, log)
        debug_level = 1 if debug else 0
        self.logger.debug('=> config file: %s' % config_path)
        self.server = smtplib.SMTP(self.get_config('mail', 'smtp'), 25)
        self.server.set_debuglevel(debug_level)
        self.server.starttls()

    def send_mail(self, toaddr, mail, fromaddr=None):
        if fromaddr is None:
            fromaddr = self.get_config('mail', 'from_addr')
        if not 'From' in mail:
            mail['From'] = fromaddr
        mail['To'] = toaddr
        if not self.dry_run:
            try:
                self.server.sendmail(fromaddr, toaddr, mail.as_string())
            except smtplib.SMTPRecipientsRefused as e:
                self.log_error(e)
            except smtplib.SMTPServerDisconnected as e:
                self.log_error(e)
        self.debug_log('Sending mail to %s' % toaddr)

    def close(self):
        self.debug_log('Closing mail server connection...')
        try:
            self.server.quit()
        except smtplib.SMTPServerDisconnected as e:
            self.log_error(e)

    @staticmethod
    def rt_mail(ticket, subject, msg):
        mail = MIMEMultipart('alternative')
        mail['References'] = 'RT-Ticket-%s@uninett.no' % ticket
        mail['Subject'] = '[uninett.no #%s] %s' % (ticket, subject)
        mail['From'] = 'NREC support <support@uh-iaas.no>'
        mail['Reply-To'] = 'support@uh-iaas.no'
        mail['X-RT-Owner'] = 'Nobody'
        mail['X-RT-Queue'] = 'NREC'
        mail['X-RT-Ticket'] = 'uninett.no #%s' % ticket
        mail.attach(MIMEText(msg, 'plain'))
        return mail

    def get_client(self):
        return self.client

    @staticmethod
    def get_mime_text(subject, body, fromaddr):
        msg = MIMEText(body)
        msg['subject'] = subject
        msg['From'] = fromaddr
        return msg

    def mail_instance_owner(self, instances, body, subject, admin=False, options=['status']):
        if not self.ksclient:
            self.logger.error('=> notify aborted: unable to find keystone client')
            return
        users = dict()
        for i in instances:
            if not admin:
                user = self.ksclient.get_by_id('user', i.user_id)
                email = self.__get_user_email(user)
            if admin or not email:
                project = self.ksclient.get_by_id('project', i.tenant_id)
                email = self.__get_project_email(project)
            if not email:
                self.logger.debug('=> unable to find owner of %s (%s)', i.name, i.id)
                continue
            if email not in users:
                users[email] = dict()
            users[email][i.name] = {
                'status': i.status,
                'az': getattr(i, 'OS-EXT-AZ:availability_zone')
            }
            if admin:
                users[email][i.name]['project'] = project.name
        # Send mail
        for user, instances in users.iteritems():
            user_instances = (
                "You are receiving this e-mail because you (or a team you're part of)\n"
                "have the following instances running in NREC:\n\n"
            )
            for server, info in instances.iteritems():
                extra = list()
                for option in options:
                    extra.append(info[option])
                user_instances += '%s (' % server + ', '.join(extra) + ')\n'
            msg = MIMEText(user_instances + body, 'plain', 'utf-8')
            msg['Subject'] = subject
            log_msg = 'sending mail to %s' % user
            self.send_mail(user, msg)
        return users

    def set_keystone_client(self, ksclient):
        self.ksclient = ksclient

    def mail_user(self, body, subject, user):
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        log_msg = 'sending mail to %s' % user
        self.send_mail(user, msg)

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
