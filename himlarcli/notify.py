import ConfigParser
import smtplib

class Notify(object):

    def __init__(self, config_path, debug=0):
        config = ConfigParser.ConfigParser()
        config.read(config_path)
        self.config = config._sections['mail']
        self.server = smtplib.SMTP(self.config['smtp'], 25)
        self.server.set_debuglevel(debug)
        self.server.starttls()

    def send_mail(self, toaddr, msg, ):
        self.server.sendmail(self.config['from_addr'], toaddr, msg.as_string())

    def close(self):
        self.server.quit()
