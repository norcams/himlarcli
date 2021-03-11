import json
import operator
import sys
import csv
from collections import OrderedDict
import locale

locale.setlocale(locale.LC_ALL, 'en_DK.UTF-8')

class Printer(object):

    VALID_OPTIONS = ['text', 'json', 'csv']
    INDENT = 2

    def __init__(self, output_format):
        if output_format in self.VALID_OPTIONS:
            self.format = output_format
        else:
            sys.exit('Printer(): Unknown format %s' % output_format)

    def output_list_dicts(self, lists, sort=True, one_line=False):
        if self.format == 'text':
            self.__list_dicts_to_text(lists=lists, sort=sort, one_line=one_line)
        elif self.format == 'json':
            self.__list_dicts_to_json(lists=lists, sort=sort)
        elif self.format == csv:
            print 'not implemented'

    def output_dict(self, objects, sort=True, one_line=False):
        if not isinstance(objects, dict):
            self.log_error('cannot output dict in printer. wrong object type')
            return
        if self.format == 'text':
            self.__dict_to_text(objects=objects, sort=sort, one_line=one_line)
        elif self.format == 'json':
            self.__dict_to_json(objects=objects, sort=sort)
        elif self.format == 'csv':
            self.__dict_to_csv(objects=objects, sort=sort)

    def output_msg(self, msg):
        if self.format == 'text':
            print "\n{}\n".format(msg)
        elif self.format == 'json':
            self.__dict_to_json(objects={'message': msg})
        elif self.format == 'csv':
            print "{};".format(msg)

    def __dict_to_json(self, objects, sort=True):
        if 'header' in objects:
            del objects['header']
        if objects:
            print json.dumps(objects, sort_keys=sort, indent=self.INDENT)

    def __list_dicts_to_text(self, lists, sort=True, one_line=False):
        for obj in lists:
            self.__dict_to_text(obj, sort=sort, one_line=one_line)

    def __list_dicts_to_json(self, lists, sort=True):
        for obj in lists:
            self.__dict_to_json(obj, sort=sort)

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
                if isinstance(v, int) or isinstance(v, float):
                    value = '{:n}'.format(v)
                else:
                    value = v
                print "%s = %s" % (k, value)
        if out_line:
            print out_line.strip()

    @staticmethod
    def __dict_to_csv(objects, order_by=0, sort=True):
        if 'header' in objects:
            del objects['header']
            print_header = True
        else:
            print_header = False
        writer = csv.DictWriter(sys.stdout,
                                fieldnames=objects.keys(),
                                dialect='excel')
        if objects:
            if print_header:
                writer.writeheader()
            if sort:
                sorted_objects = OrderedDict(sorted(objects.items()))
            else:
                sorted_objects = objects
            writer.writerow(sorted_objects)

    @staticmethod
    def log_error(msg, code=0):
        sys.stderr.write("%s\n" % msg)
        if code > 0:
            sys.exit(code)
