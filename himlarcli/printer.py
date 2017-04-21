import json
import operator
import sys

class Printer(object):

    VALID_OPTIONS = ['text', 'json']
    INDENT = 2

    def __init__(self, output_format):
        if output_format in self.VALID_OPTIONS:
            self.format = output_format
        else:
            sys.exit('Printer(): Unknown format %s' % output_format)

    def output_dict(self, objects):
        if self.format == 'text':
            self.__dict_to_text(objects)
        elif self.format == 'json':
            self.__dict_to_json(objects)

    def __dict_to_json(self, objects):
        if 'header' in objects:
            del objects['header']
        print json.dumps(objects, sort_keys=True, indent=self.INDENT)

    @staticmethod
    def __dict_to_text(objects, order_by=0):
        print ""
        sorted_objects = sorted(objects.items(), key=operator.itemgetter(order_by))
        if 'header' in objects:
            print "".ljust(80, "=")
            print "  %s" % objects['header'].ljust(76)
            print "".ljust(80, "=")
        for k, v in sorted_objects:
            if k == 'header':
                continue
            elif isinstance(v, list):
                for i in v:
                    print i
            else:
                print "%s = %s" % (k, v)
