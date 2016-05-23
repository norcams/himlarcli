import ConfigParser
import smtplib

class Notify(object):

    def __init__(self, config_path, debug=False):
        if debug:
            debug_level = 1
        else:
            debug_level = 0
        config = ConfigParser.ConfigParser()
        config.read(config_path)
        self.config = config._sections['mail']
        self.server = smtplib.SMTP(self.config['smtp'], 25)
        self.server.set_debuglevel(debug_level)
        self.server.starttls()

    def send_mail(self, toaddr, msg, ):
        msg['From'] = self.config['from_addr']
        msg['To'] = toaddr
        self.server.sendmail(self.config['from_addr'], toaddr, msg.as_string())

    def close(self):
        self.server.quit()
