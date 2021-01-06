import binascii
import operator
import re
from inspect import getframeinfo, stack
import importlib

import Swoop

from intersect import doIntersect, Point
from Bunch import Bunch

def mm_to_mil(mm):
    return 39.3701 * mm
def mil_to_mm(mil):
    return mil/39.3701

def mm_to_inch(mm):
    return mm/25.4
def inch_to_mm(inch):
    return inch * 25.4

checker_options = Bunch(
    silkscreen_min_size = 0.9,
    silkscreen_ratio = 8,
    silkscreen_fonts = ['vector'],
    green_led_pin = "PG0(DIG3)",
    red_led_pin = "PG1(DIG1)",
    green_led_resistor= "SMD-2012-0805-330",
    red_led_resistor = "SMD-2012-0805-330",
    max_clock_net_turns = 11,
    high_current_min_width = mil_to_mm(10),
    rf_min_width = mil_to_mm(40),
    expected_regulated_decoupling_caps=7,
    expected_battery_decoupling_caps=2,#5,
    high_current_net_class_names=["HIGH_CURRENT", "HIGHCURRENT","HighAmps", "HIGH-I"],
    power_net_class_names=["PWR", "pwr"],
    power_and_ground_names = ["VCC", "VDD", "3V3", "+3V3", "GND", "BAT_GND", "3V", "VBAT", "5V"],
    symbols_that_need_no_name = ["FRAME_B_L", "DOCFIELD"],
    ground_device_sets_names = ["GND", "BAT_GND"],
    power_device_set_names = ["3V", "VCC", "V3", "VBAT", "+3V3"]
)



html_output = True



def output_format(p, type=None):
    if isinstance(p, str):
        name = p
    else:
        name = p.get_name()

    if html_output:
        if isinstance(p, Swoop.Part) or type == "part":
            return "<span class='swoop-lint-part'>{}</span>".format(name)
        elif isinstance(p, Swoop.Element) or type == "part":
            return "<span class='swoop-lint-part'>{}</span>".format(name)
        elif isinstance(p, Swoop.Net) or isinstance(p, Swoop.Signal) or type == "net":
            return "<span class='swoop-lint-net'>{}</span>".format(name)
        elif isinstance(p, Swoop.Pin) or type == "pin":
            return "<span class='swoop-lint-pin'>{}</span>".format(name)
        else:
            return name
    else:
        return name


class ChainLink(object):

    def __init__(self):
        super(object, self).__init__()


class Pin(ChainLink):
    def __init__(self, name=None, select=None, description=None):
        super(ChainLink, self).__init__()
        self.name = listify(name)
        self.select = select
        self.description = description


    def __str__(self):
        if html_output:
            return self.html()
        else:
            return "Pin({})".format(self.get_string())

    def get_string(self):
        if self.name:
            return "|".join(self.name)
        elif self.select:
            return "{}".format(self.description if self.description else "custom")
        else:
            return "??"

    def html(self):
        return "<span class='swoop-lint-pin'>{}</span>".format(self.get_string())

    def match(self, pin):
        return all([not self.name or pin.get_pin() in self.name,
                    not self.select or self.select(pin)])


def listify(l):
    if l is None:
        return None
    return l if isinstance(l, list) else [l]

class Part(ChainLink):
    def __init__(self, name=None, longname=None, deviceset=None, device=None, select=None, part=None, description=None, value=None):
        super(ChainLink, self).__init__()

        self.name = listify(name)
        self.deviceset = listify(deviceset)
        self.device = listify(device)
        self.longname = listify(longname)
        self.part = listify(part)
        self.description = description
        self.select = select
        self.value = listify(value)

    def get_string(self):
        if self.name:
            return "|".join(self.name)
        elif self.deviceset:
            return "|".join(self.deviceset)
        elif self.device:
            return "|".join(self.device)
        elif self.longname:
            return "|".join(self.longname)
        elif self.select:
            return self.description if self.description else "custom"
        elif self.part:
            return "|".join([x.get_name() for x in self.part])
        else:
            return "??"

    def __str__(self):

        if html_output:
            return self.html()
        else:
            return "Part({})".format(self.get_string())

    def html(self):
        return "<span class='swoop-lint-part'>{}</span>".format(self.get_string())

    def match(self, part):
        return all([not self.part or part in self.part,
                    not self.longname or part.get_deviceset() + part.get_device() in self.longname,
                    not self.deviceset or part.get_deviceset() in self.deviceset,
                    not self.device or part.get_device() in self.device,
                    not self.select or self.select(part),
                    not self.value or (part.get_value() and part.get_value().upper() in map(lambda x:x.upper(), self.value))])


class Net(ChainLink):
    def __init__(self, name=None,select=None, net=None, description=None):
        super(ChainLink, self).__init__()
        self.name = name
        self.select = select
        self.net = net
        self.description = description

    def get_string(self):
        if self.name:
            return "{}".format(self.name)
        elif self.net:
            return "{}".format(self.net.get_name())
        elif self.select:
            return "{}".format(self.description if self.description else "custom")
        else:
            return "??"

    def __str__(self):
        if html_output:
            return self.html()
        else:
            return "Net({})".format(self.get_string())

    def html(self):
        return "<span class='swoop-lint-net'>{}</span>".format(self.get_string())

    def match(self, net):
        return all([not self.name or self.name == net.get_name(),
                    not self.select or self.select(net),
                    not self.net or self.net == net])


def str_pattern(path=(), pattern=()):
    if path:
        path_str = ":".join(map(lambda x: x.get_name(), path))
    else:
        path_str = ""

    if pattern:
        if html_output:
            pat_str = '<div class="swoop-lint-pattern"> '+ "".join(map(str, pattern)) + '</div>'
            #print pat_str
        else:
            pat_str = " ".join(map(str, pattern))
    else:
        pat_str = ""

    if path:
        return "{}: {}".format(path_str, pat_str)
    else:
        return pat_str


class FailedMatchException(Exception):
    pass


class CheckerContext(object):
    def __init__(self):
        pass

class Checker(object):
    def __init__(self, errors, fix, context=None, sch=None, brd=None, lbrs=None, options=None):
        assert isinstance(errors, ErrorCollector)
        self.errors = errors
        self.sch = sch
        self.brd = brd
        self.lbrs = lbrs if lbrs else []
        self.fix = fix
        self.ctx = context or CheckerContext()
        if options is None:
            self.options = {}
        else:
            self.options = options

    def do_check(self):
        pass

    def check(self):
        self.do_check()
        return (self.errors, self.ctx)

    def error(self, message, inexcusable=False):
        caller = getframeinfo(stack()[1][0])
        self.errors.record_error(self.sch, message, note="{}:{}".format(caller.filename.split("/")[-1], caller.lineno), inexcusable=inexcusable)
    def info(self, message):
        caller = getframeinfo(stack()[1][0])
        self.errors.record_info(self.sch, message, note="{}:{}".format(caller.filename.split("/")[-1], caller.lineno))
    def warn(self, message, inexcusable=False):
        caller = getframeinfo(stack()[1][0])
        self.errors.record_warning(self.sch, message, note="{}:{}".format(caller.filename.split("/")[-1], caller.lineno), inexcusable=inexcusable)

    def do_match(self, path, pattern, solutions):
        if len(pattern) == 0:
            solutions.append(path)
            return
        tail = path[-1]

        if isinstance(tail, Swoop.Part):

            if len(pattern) == 2:
                pin_link = pattern[0]
                assert isinstance(pin_link, Pin)
                net_link = pattern[1]
                assert isinstance(net_link, Net), "{}".format(net_link)

                nets = (Swoop.From(self.sch)
                        .get_sheets()
                        .get_nets()
                        .filtered_by(lambda x: net_link.match(x))
                        .get_segments()
                        .get_pinrefs()
                        .filtered_by(lambda x: pin_link.match(x) and x.get_part() == tail.get_name())
                        .get_parent().get_parent())
                for n in nets:
                    self.do_match(path + [n], pattern[2:], solutions)

            elif len(pattern) > 2:
                initial_pin_link = pattern[0]
                assert isinstance(initial_pin_link, Pin)
                net_link = pattern[1]
                assert isinstance(net_link, Net)
                terminal_pin_link = pattern[2]
                assert isinstance(terminal_pin_link, Pin)
                part_link = pattern[3]
                assert isinstance(part_link, Part), "Bad pattern: {}".format(str_pattern(pattern=pattern))

                nets = (Swoop.From(self.sch)
                        .get_sheets()
                        .get_nets()
                        .filtered_by(lambda x: net_link.match(x))
                        .get_segments()
                        .get_pinrefs()
                        .filtered_by(lambda x: x.get_part() == tail.get_name())
                        .get_parent()
                        .get_parent()
                        .unique())

                for n in nets:
                    refs = (Swoop.From(n)
                            .get_segments()
                            .get_pinrefs())
                    initial_pin_matches = refs.filtered_by(lambda x: initial_pin_link.match(x) and x.get_part() == tail.get_name())
                    terminal_pin_matches = refs.filtered_by(lambda x: terminal_pin_link.match(x))

                    if (len(initial_pin_matches)):
                        parts = map(lambda x: self.sch.get_part(x), terminal_pin_matches.get_part())
                        for p in parts:
                            if part_link.match(p) and p != tail:
                                self.do_match(path + [n, p], pattern[4:], solutions)

            else:
                raise Exception("Couldn't process pattern {}".format(str_pattern(path, pattern)))
        else:
            raise Exception("Patterns must start with a part.")

    def match(self, pattern):
        solutions = []

        for i in range(0,len(pattern)):
            if isinstance(pattern[i], Swoop.Part):
                pattern[i] = Part(part=pattern[i])
            elif isinstance(pattern[i], Swoop.Net):
                pattern[i] = Net(net=pattern[i])

        link = pattern[0]
        if isinstance(link, Part):
            options = Swoop.From(self.sch).get_parts().filtered_by(lambda x: link.match(x))
        elif isinstance(link, Net):
            options = Swoop.From(self.sch).get_sheets().get_nets().filtered_by(lambda x: link.match(x))
        else:
            raise Exception("First link in pattern must be Net or Part: {}".format(link))

        for o in options:
            path=[o]
            self.do_match(path, pattern[1:], solutions)

        return solutions


    def match_one(self, pattern, error="", warning=""):
        r = self.match(pattern)
        if len(r) != 1:
            if error or warning:
                s = (error + warning + "<br/>Searching for {pp}<br/>Found {c} matching paths, but should have found 1.  Here are the matches (if any):<br/> {matches}").format(c=len(r), pattern=pattern, pp=str_pattern(pattern=pattern), matches="<br/>".join(map(str_pattern,r)))
                if not html_output:
                    s = s.replace("<br/>", "\n\t")
                if error:
                    self.error(s)
                if warning:
                    self.warn(s)
                return [None] * len(filter(lambda x: isinstance(x, Net) or isinstance(x, Part), pattern))
            else:
                raise FailedMatchException(u"Wanted one match, got {}: {} {}".format(len(r), str_pattern(pattern=pattern), "\n".join(map(str_pattern,r))))
        else:
            #print "Pattern {} matched on {}".format(str_pattern(pattern=pattern), str_pattern(path=r[0]))
            return r[0]

    def match_none(self, pattern, error):
        r = self.match(pattern)

        if len(r) != 0:
            if error:
                #self.error((error + "({pattern} found {path})").format(pattern=str_pattern(pattern=pattern),path=str_pattern(path=r[0])))
                self.error((error + " {pattern} found {path}").format(pattern=str_pattern(pattern=pattern),path=str_pattern(path=r[0])))
                return [None] * len(filter(lambda x: isinstance(x, Net) or isinstance(x, Part), pattern))
            else:
                raise FailedMatchException(u"Too many matches: {} {}".format(str_pattern(pattern=pattern), "\n".join(map(str_pattern,r))))
        else:
            return []

    def signal_length(self, name):
        return Swoop.From(self.brd.get_signal(name)).get_wires().get_length().reduce(operator.add,0)


    def check_intersections(self, routed_wires):
        if not routed_wires:
            return

        t = routed_wires[0]
        if isinstance(t.get_parent(), Swoop.Segment):
            get_net = lambda x: x.get_parent().get_parent()
        else:
            get_net = lambda x: x.get_parent()

        for (i, w1) in enumerate(sorted(routed_wires)):
            w1x1, w1y1, w1x2, w1y2 = w1.get_points()
            for (j, w2) in enumerate(sorted(routed_wires)):
                if j <= i:
                    continue
                w2x1, w2y1, w2x2, w2y2 = w2.get_points()

                if doIntersect(Point(w1x1, w1y1),
                                Point(w1x2, w1y2),
                                Point(w2x1, w2y1),
                                Point(w2x2, w2y2)):
                    if get_net(w1) is not get_net(w2) and w1.get_layer() == w2.get_layer():
                        self.error(
                            "The segment of {w1} from ({w1x1}, {w1y1}) to ({w1x2}, {w1y2}) intersects with the segment of {w2} from ({w2x1}, {w2y1}) to ({w2x2}, {w2y2}).".format(
                                w1=output_format(get_net(w1)),
                                w1x1=w1x1,
                                w1y1=w1y1,
                                w1x2=w1x2,
                                w1y2=w1y2,
                                w2x1=w2x1,
                                w2y1=w2y1,
                                w2x2=w2x2,
                                w2y2=w2y2,
                                w2=output_format(get_net(w2))))

    def is_aligned(self, d, grid):
        x = round(d / grid, 0)
        return round(x * grid, 2) == round(d, 2)

class NoopChecker(Checker):

    def do_check(self):
        if self.sch:
            self.info("Examined schematic {}".format(self.sch.get_filename()))

        if self.brd:
            self.info("Examined board {}".format(self.brd.get_filename()))

        for l in self.lbrs:
            self.info("Examined library {}".format(l.get_filename()))


class CheckerSequence(Checker):
    def __init__(self, checkers, *args, **kwargs):
        super(CheckerSequence, self).__init__(*args, **kwargs)
        self.checkers = checkers

    def do_check(self):
        for Checker in self.checkers:
            Checker(sch=self.sch, errors=self.errors, context=self.ctx, brd=self.brd, lbrs=self.lbrs, fix=self.fix).check()

def CheckSet(checkers):
    class C(CheckerSequence):
        def __init__(self, *args, **kwargs):
            super(C, self).__init__(checkers, *args, **kwargs)

    return C

def count_pins(part):
    return len(part.find_deviceset().get_gates()[0].find_symbol().get_pins())

def bounding_box(items):
    if isinstance(items, Swoop.From):
        items = items.unpack()
    elif not isinstance(items, list):
        items = [items]

    bounds_points = reduce(lambda x,y: x+y, map(lambda x:x.get_bounds_points(), items), [])
    xs = map(lambda a: a[0], bounds_points)
    ys = map(lambda a: a[1], bounds_points)
    return (min(*xs), min(*ys), max(*xs), max(*ys))

def bounding_box_size(items):
    x1, y1, x2, y2 = bounding_box(items)
    return abs(x2 - x1), abs(y2 - y1)

def bounding_box_area(items):
    x,y = bounding_box_size(items)
    return x * y

class Error(object):

    def __init__(self, path, error, level, index, context="", excused=False, inexcusable=False):
        self.path = path
        self.error = error
        self.level = level
        self.index = index
        self.excused = excused
        self.context = context
        self.inexcusable = inexcusable

    def _asdict(self):
        return dict(path=self.path,
                    error=self.error,
                    level=self.level,
                    index=self.index,
                    excused=self.excused,
                    context=self.context,
                    inexcusable=self.inexcusable)

    def get_full_string(self):
        return self.path + self.error

    def render_message(self):
        return u"{}: {} -- {}".format(self.level, self.path, self.error)

    def __str__(self):
        return u"{} ({}:{})".format(self.render_message(), self.context, self.hash())

    def hash(self):
        hash_message = self.render_message()
        hash_message = re.sub("[^:].*/", "", hash_message) # Trim path to file, if present
        return "{:08X}".format(abs(binascii.crc32(hash_message)))


pretty_print_map={"Deviceset": "Device",
                  "Device": "Variant"
                  }


class NestedError(object):
    def __init__(self, ec, efp):
        self.ec = ec
        if isinstance(efp, str):
            ec.push_path(efp)
            self.needs_pop = True
        elif hasattr(efp, "get_name"):
            if efp.__class__.__name__ in pretty_print_map:
                t = pretty_print_map[efp.__class__.__name__]
            else:
                t = efp.__class__.__name__
            ec.push_path(u"{}".format(efp.get_name()))
            self.needs_pop = True
        else:
            self.needs_pop = False

    def __enter__(self):
        return self.ec

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.needs_pop:
            self.ec.pop_path()


class ErrorCollector(object):
    def __init__(self):
        self.errors=[]
        self.path=[]

    def load_json(self, json):
        for i in json:
            self.errors.append(Error(**i))

    def dump_json(self):
        return map(lambda x:x._asdict(), self.errors)

    def push_path(self, path):
        self.path.append(path)
    def pop_path(self):
        self.path = self.path[:-1]


    def record(self, efp, error, context="", level=None, inexcusable=False):
        if not level:
            level = "Error"

        if hasattr(efp, "get_name"):
            self.errors.append(Error(u"{}:{}".format(u":".join(self.path), efp.get_name()), error, level=level, index=len(self.errors), context=context, inexcusable=inexcusable))
        elif isinstance(efp, str):
            self.errors.append(Error(u"{}:{}".format(u":".join(self.path), efp), error, level=level, index=len(self.errors), context=context, inexcusable=inexcusable))
        else:
            self.errors.append(Error(u":".join(self.path), error, level, index=len(self.errors), context=context, inexcusable=inexcusable))

    def record_error(self, efp,error, note="", inexcusable=False):
        return self.record(efp,
                           error,
                           note,
                           None,
                           inexcusable=inexcusable)

    def record_warning(self, efp,error, note="", inexcusable=False):

        return self.record(efp,
                           error,
                           note,
                           "Warning",
                           inexcusable=inexcusable)

    def record_info(self, efp,error, note=""):
        return self.record(efp,
                           error,
                           note,
                           "Info")

    def get_errors(self):
        return self.errors

    def nest(self, efp):
        return NestedError(self, efp)

    def filter_by_hash(self, approved_errors):
        self.errors = [e for e in self.errors if e.hash() not in approved_errors]