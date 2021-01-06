import re

from SwoopChecker import Checker, NestedError, output_format, checker_options
from LibraryStyle import LibraryLint
import Swoop
import math


class BoardLint(Checker):

    def do_check(self):
        if not self.brd:
            return

        self.check_routing()
        self.check_libraries()
        self.check_outline()
        self.check_names()
        self.check_placement()
        self.check_vias()
        self.check_pours()
        self.check_displayed_attributes()

        LibraryLint(lbrs=Swoop.From(self.brd).get_libraries(),
                    errors=self.errors,
                    fix=self.fix,
                    options=self.options).check()

    def check_pours(self):
        with self.errors.nest(self.brd.get_filename()):

            for p in Swoop.From(self.brd).get_signals().get_polygons():
                if p.get_isolate() not in [0, 0.0, None]:
                    self.warn("A pour in {} has non-zero 'isolate'.  This is unusual, and probably not what you want.".format(p.get_parent().get_name()))

    def check_displayed_attributes(self):
        with self.errors.nest(self.brd.get_filename()):
            names = Swoop.From(self.brd).get_elements().get_attributes().with_name("NAME").with_display(True)
            for t in names:
                #fixme The default value for ratio is not working right for attributes.  so check for != None
                if t.get_size() < checker_options.silkscreen_min_size or not (t.get_ratio() == checker_options.silkscreen_ratio or t.get_ratio() == None) or t.get_font() not in checker_options.silkscreen_fonts:
                    if False:#self.fix:1
                        t.set_size(checker_options.silkscreen_min_size).set_ratio(checker_options.silkscreen_ratio).set_font(
                            checker_options.silkscreen_fonts[0])
                    else:
                        self.warn(
                            u"'{}' in reference designator has wrong geometry (size={}mm, ratio={}%, font={}).  Should be {}mm, {}%, and one of these fonts that will render properly on the board during manufacturing: {}.".format(
                                t.get_parent().get_name(),
                                t.get_size(), t.get_ratio(), t.get_font(),
                                checker_options.silkscreen_min_size,
                                checker_options.silkscreen_ratio,
                                ", ".join(checker_options.silkscreen_fonts)), inexcusable=True)

            sizes = names.get_size().unique()

            if len(sizes) > 1:
                self.warn("Your reference designators are not all the same size.  I found these sizes: {}".format(", ".join(map(str,sizes))))

            values = Swoop.From(self.brd).get_elements().get_attributes().with_name("VALUE").with_display(True)

            for t in values:
                if t.get_size() < checker_options.silkscreen_min_size or (t.get_ratio() != checker_options.silkscreen_ratio and t.get_ratio() != None)   or t.get_font() not in checker_options.silkscreen_fonts:
                    if False:#self.fix:
                        t.set_size(checker_options.silkscreen_min_size).set_ratio(checker_options.silkscreen_ratio).set_font(
                            checker_options.silkscreen_fonts[0])
                    else:
                        self.warn(
                            u"'{}' in value on board has wrong geometry (size={}mm, ratio={}%, font={}).  Should be {}mm, {}%, and one of these fonts that will render properly on the board during manufacturing: {}.".format(
                                t.get_parent().get_name(),
                                t.get_size(), t.get_ratio(), t.get_font(),
                                checker_options.silkscreen_min_size,
                                checker_options.silkscreen_ratio,
                                ", ".join(checker_options.silkscreen_fonts)), inexcusable=True)

            sizes = values.get_size().unique()

            if len(sizes) > 1:
                self.warn("Your size labels are not all the same size.  I found these sizes: {}".format(", ".join(map(str,sizes))))

    def check_alignment(self, part, grid):
        scale = 10000
        grid = int(round(grid * scale))
        x = int(round(part.get_x() * scale))
        y = int(round(part.get_y() * scale))
        return (x % grid) != 0 or (y % grid) != 0

    def check_vias(self):
        with self.errors.nest(self.brd.get_filename()):
            for s in Swoop.From(self.brd.get_signals()):
                for v in s.get_vias():
                    if v.get_drill() > 0.8:
                        self.warn("The via at ({},{}) on {} is too big ({}mm). You probably don't want vias larger than 0.8mm".format(v.get_x(), v.get_y(), output_format(s), v.get_drill()))

    def check_placement(self):
        with self.errors.nest(self.brd.get_filename()):
            for e in Swoop.From(self.brd).get_elements():
                grid = 0.5
                if self.check_alignment(e, grid):
                    self.warn("Part {} at ({}, {}) is not not aligned to {}mm grid.".format(e.get_name(), e.get_x(), e.get_y(), grid))

                for a in Swoop.From(e).get_attributes().with_display(True):
                    if a.get_name() == "VALUE" and a.get_value() in ["", None]:  # If value is "" then it doesn't show up and there is really no way to fix it in eagle.
                        continue
                    grid = 0.1
                    if self.check_alignment(a, grid):
                        if self.fix:
                            a.set_x(round(a.get_x()/grid) * grid)
                            a.set_y(round(a.get_y()/grid) * grid)
                        else:
                            self.warn("Label '{}' of {} at ({}, {}) in layer {} is not aligned to {}mm grid. ".format(a.get_name(), e.get_name(), a.get_x(), a.get_y(), a.get_layer(), grid ))


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
            dims = Swoop.From(self.brd).get_plain_elements().with_type(Swoop.Wire).with_layer("Dimension")
            self.info("Found {} lines in layer 'Dimension'".format(len(dims)))
            if dims.filtered_by(lambda x:x.get_width() < 0.01).count():
                self.warn("Lines in 'Dimension' should have width >= 0.01mm.  Otherwise some CAM viewers have trouble displaying them the board outline.", inexcusable=True)

            non_wire = Swoop.From(self.brd).get_plain_elements().without_type(Swoop.Hole).without_type(Swoop.Wire).with_layer("Dimension")
            if len(non_wire):
                self.warn("You things in your Dimension layer other than lines and arcs.  You probably don't want that.", inexcusable=True)

    def check_libraries(self):
        with self.errors.nest(self.brd.get_filename()):
            lbr_list = self.lbrs

            libs = {l.get_library().get_name().upper(): l for l in lbr_list}

            for part in self.brd.get_elements():
                library = part.get_library().upper()
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