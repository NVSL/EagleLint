import re

from SwoopChecker import Checker, NestedError, output_format
from LibraryStyle import LibraryLint
import Swoop
import math


class BoardLint(Checker):

    def do_check(self):
        if not self.brd:
            return

        self.check_routing()
        #self.check_attrs()
        self.check_libraries()
        self.check_outline()
        self.check_names()
        self.check_placement()

        LibraryLint(lbrs=Swoop.From(self.brd).get_libraries(),
                    errors=self.errors,
                    fix=self.fix,
                    options=self.options).check()

    def check_alignment(self, part, grid):
        scale = 10000
        grid = int(round(grid * scale))
        x = int(round(part.get_x() * scale))
        y = int(round(part.get_y() * scale))
        return (x % grid) != 0 or (y % grid) != 0

    def check_placement(self):
        with self.errors.nest(self.brd.get_filename()):
            for e in Swoop.From(self.brd).get_elements():
                grid = 1.0
                if self.check_alignment(e, grid):
                    self.warn("Part {} at ({}, {}) is not not aligned to {}mm grid.".format(e.get_name(), e.get_x(), e.get_y(), grid))

                for a in Swoop.From(e).get_attributes().with_display(True):
                    grid = 0.1
                    if self.check_alignment(a, grid):
                        if self.fix:
                            print "fixing"
                            a.set_x(round(a.get_x()/grid) * grid)
                            a.set_y(round(a.get_y()/grid) * grid)
                        else:
                            self.warn("Label '>{}' of {} at ({}, {}) in layer {} is not aligned to {}mm grid. ".format(a.get_name(), e.get_name(), a.get_x(), a.get_y(), a.get_layer(), grid ))


    def check_names(self):
        with self.errors.nest(self.brd.get_filename()):
            for p in Swoop.From(self.brd).get_elements().get_name():
                m = re.match("[A-Z][A-Z]?\d+", p)
                if not m and self.sch.get_part(p):
                    self.warn(
                        "The name of part '{}' is too long.  It should be at most two capital letters followed numbers.".format(
                            p))

    def check_outline(self):
        with self.errors.nest(self.brd.get_filename()):
            dims = Swoop.From(self.brd).get_plain_elements().without_type(Swoop.Hole).with_layer("Dimension")
            self.info("Found {} lines in layer 'Dimension'".format(len(dims)))
            if dims.with_width(0).count():
                self.error("Lines in 'Dimension' should have non-zero width.", inexcusable=True)

    def check_libraries(self):
        with self.errors.nest(self.brd.get_filename()):
            lbr_list = self.lbrs

            libs = {l.get_library().get_name(): l for l in lbr_list}

            for part in self.brd.get_elements():
                library = part.get_library()
                lib = libs.get(library)
                if lib is None:
                    self.errors.record_warning(part, "Can't find library '{}' for part '{}'".format(library, part.get_name()))
                else:
                    with self.errors.nest(part):
                        package = lib.get_library().get_package(part.get_package())
                        if not package:
                            self.warn(u"Can't find package {} in library {}".format(part.get_package(), lib.get_library().get_name()))
                        elif not part.find_package().is_equal(package):
                            self.warn(
                                u"Package {} doesn't match package in library '{}'.  You need to update the libraries in your board: 'Library->Update...' or 'Library->Update All'".format(
                                    package.get_name(),
                                    library), inexcusable=True)

    # I'm not sure why we are checking this.  Why do we require that the element have all the attribute tags?  Is it because the list has to match the library?
    # def check_attrs(self):
    #     for t in Swoop.From(self.brd).get_elements():
    #         for attr in self.required_deviceset_attributes:
    #             if not t.get_attribute(attr) or not t.get_attribute(attr).get_value():
    #                 t.add_attribute(Swoop.Attribute().set_name(attr).set_value("Unknown").set_display("off").set_layer("Document"))

    def check_routing(self):
        with NestedError(self.errors, self.brd.get_filename()):

            unrouted = Swoop.From(self.brd).get_signals().get_wires().with_width(0.0)
            if unrouted.count() > 0:
                self.error(u"You have unrouted nets: {}".format(
                    " ".join(map(output_format, unrouted.get_parent().unique().sort()))), inexcusable=True)

            routed_wires = Swoop.From(self.brd).get_signals().get_wires().without_width(0.0)

            self.check_intersections(routed_wires)

            for w in routed_wires:
                with NestedError(self.errors, w):
                    x1, y1, x2, y2 = w.get_points()

                    if abs(x1 - x2) < 0.1 or abs(y1 - y2) < 0.1 or abs(abs(x1 - x2) - abs(y1 - y2)) < 0.1 or w.get_length() < 2:
                        pass
                    else:
                        self.warn(
                            "Net routed at odd angle: {} centered at ({}, {}) in layer {}.  Net should only be vertical, horizontal, or diagonal (i.e., 45 degrees).".format(output_format(w.get_parent()),
                                                                                                  (x1 + x2) / 2,
                                                                                                  (y1 + y2) / 2,
                                                                                                  w.get_layer()))