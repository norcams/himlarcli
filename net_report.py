#!/usr/bin/env python
import json

from himlarcli import utils
from himlarcli.keystone import Keystone
from himlarcli.mail import Mail
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer

utils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

# Region
if hasattr(options, "region"):
    regions = kc.find_regions(region_name=options.region)
else:
    regions = kc.find_regions()


def get_network_list():
    networks = []
    for region in regions:
        logger.debug("=> region %s", region)
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        instances = nc.get_all_instances()
        for i in instances:
            instance = {"id": i.id}
            # instance["power_state"] = getattr(i, "OS-EXT-STS:power_state")
            instance["status"] = i.status.lower()
            # print(dir(i))
            for k, v in i.networks.items():
                instance["network"] = {"type": k, "IP": v}
            networks.append(instance)
    return networks


def action_list():
    networks = get_network_list()
    pretty = json.dumps(networks, indent=2)
    print(pretty)


def action_mail():
    networks = get_network_list()

    # Set common mail parameters
    mail = utils.get_client(Mail, options, logger)
    fromaddr = "support@nrec.no"
    bccaddr = 'iaas-logs@usit.uio.no'
    attachment_payload = json.dumps(networks, indent=2)
    body_content = f"Dump of used NREC IP addresses in {', '.join(regions)} attached."
    msg = mail.create_mail_with_txt_attachment(
        options.subject, body_content, attachment_payload, "resources.json", fromaddr
    )

    mail.send_mail(options.email, msg, fromaddr, bcc=bccaddr, msgid="report")
    logger.debug("=> send mail to %s", options.email)


# Run local function with the same name as the action (Note: - => _)
action = locals().get("action_" + options.action.replace("-", "_"))
if action is not None:
    action()
else:
    utils.sys_error(f"Function action_{options.action}() not implemented")
