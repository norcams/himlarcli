import ConfigParser
import smtplib

class Notify(object):

    def __init__(self, config_path):
        config = ConfigParser.ConfigParser()
        config.read(config_path)
        self.config = config._sections['mail']

    def send_mail(self, toaddr, msg, debug=0):
        server = smtplib.SMTP(self.config['smtp'], 25)
        server.set_debuglevel(debug)
        server.starttls()
        server.sendmail(self.config['from_addr'], toaddr, msg.as_string())
        server.quit()
