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
            log_msg = 'Sending mail to %s' % toaddr
            try:
                self.server.sendmail(fromaddr, toaddr, mail.as_string())
            except smtplib.SMTPRecipientsRefused as e:
                self.log_error(e)
        else:
            log_msg = 'DRY-RUN:' + mail.as_string()
        self.logger.debug('=> %s', log_msg)

    def close(self):
        self.server.quit()

    @staticmethod
    def rt_mail(ticket, subject, msg):
        mail = MIMEMultipart('alternative')
        mail['References'] = 'RT-Ticket-%s@uninett.no' % ticket
        mail['Subject'] = '[uninett.no #%s] %s' % (ticket, subject)
        mail['From'] = 'UH-IaaS support <support@uh-iaas.no>'
        mail['Reply-To'] = 'support@uh-iaas.no'
        mail['X-RT-Owner'] = 'Nobody'
        mail['X-RT-Queue'] = 'UH-IaaS'
        mail['X-RT-Ticket'] = 'uninett.no #%s' % ticket
        mail.attach(MIMEText(msg, 'plain'))
        return mail

    def get_client(self):
        return self.client
