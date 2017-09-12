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

    def output_dict(self, objects, sort=True, one_line=False):
        if self.format == 'text':
            self.__dict_to_text(objects=objects, sort=sort, one_line=one_line)
        elif self.format == 'json':
            self.__dict_to_json(objects=objects, sort=sort)

    def __dict_to_json(self, objects, sort=True):
        if 'header' in objects:
            del objects['header']
        if objects:
            print json.dumps(objects, sort_keys=sort, indent=self.INDENT)

    @staticmethod
    def __dict_to_text(objects, order_by=0, sort=True, one_line=False):
        if sort:
            sorted_objects = sorted(objects.items(), key=operator.itemgetter(order_by))
        else:
            sorted_objects = objects.items()
        if 'header' in objects:
            print "".ljust(80, "=")
            print "  %s" % objects['header'].ljust(76)
            print "".ljust(80, "=")
        out_line = str()
        for k, v in sorted_objects:
            if k == 'header':
                continue
            elif isinstance(v, list):
                print '%s =' % k
                for i in v:
                    print "  %s" % i
            elif one_line:
                out_line += '%s ' % v
            else:
                print "%s = %s" % (k, v)
        if out_line:
            print out_line.strip()
