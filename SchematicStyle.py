import math

from LibraryStyle import LibraryLint
from SwoopChecker import Checker, NestedError, checker_options, output_format
import Swoop

class SchematicLint(Checker):

    def check_libraries(self):
        errors = self.errors
        sch = self.sch
        lbr_list = self.lbrs

        libs = {l.get_library().get_name(): l for l in lbr_list}

        for part in sch.get_parts():
            library = part.get_library()
            lib = libs.get(library)
            if lib is None:
                with NestedError(errors, part):
                    if library not in (self.options.get("ignored_missing_libraries") or []):
                        self.warn("Can't find library '{}' for part '{}'".format(library, part.get_name()))
            else:

                sch_deviceset = part.find_deviceset()
                with NestedError(errors, sch_deviceset):
                    lib_deviceset = libs[library].get_library().get_deviceset(sch_deviceset.get_name())

                    syms = Swoop.From(sch_deviceset).get_gates().find_symbol().unique()
                    for s in syms:

                        with errors.nest(s):
                            symbol = lib.get_library().get_symbol(s.get_name())
                            if not symbol:
                                self.warn(u"Symbol is not in library {}".format(library))
                            elif not s.is_equal(symbol):
                                self.warn(u"Symbol doesn't match symbol in library '{}'.  You need to update the libraries in your schematic: 'Library->Update...' or 'Library->Update All'".format(library))

                    pkgs = Swoop.From(sch_deviceset).get_devices().find_package().unique()
                    for p in pkgs:
                        with errors.nest(p):
                            package = lib.get_library().get_package(p.get_name())
                            if not package:
                                self.warn(u"Package is not in library {}".format(library))
                            elif not p.is_equal(package):
                                self.warn(u"Package doesn't match package in library '{}'.  You need to update the libraries in your schematic: 'Library->Update...' or 'Library->Update All'".format(library))

                    if lib_deviceset is None:
                        errors.record(None,
                                      "Device '{}' is not in library '{}'".format(sch_deviceset.get_name(), library))
                    else:
                        sch_device = part.find_device()
                        with NestedError(errors, sch_device):
                            lib_device = lib_deviceset.get_device(sch_device.get_name())
                            if lib_device is None:
                                errors.record(sch_device,
                                              "Variant '{}' is not in library '{}'".format(sch_device.get_name(),
                                                                                           library))
                            else:
                                try:
                                    if not sch_device.is_equal(lib_device):
                                        errors.record(None, "Variant '{}' is different in library '{}'.  You need to update the libraries in your schematic: 'Library->Update...' or 'Library->Update All'".format(
                                            sch_device.get_name(), library))

                                    sch_technology = part.find_technology()
                                    with NestedError(errors, sch_technology):
                                        lib_technology = lib_device.get_technology(sch_technology.get_name())
                                        if lib_technology is None:
                                            errors.record(None, "Technology '{}' is not in library '{}'.  You need to update the libraries in your schematic: 'Library->Update...' or 'Library->Update All'".format(
                                                sch_technology.get_name(), library))
                                        else:
                                            if not sch_technology.is_equal(lib_technology):
                                                errors.record(None,
                                                              "Attributes for variant '{}' are different in library '{}'. You need to update the libraries in your schematic: 'Library->Update...' or 'Library->Update All'".format(
                                                                  sch_device.get_name(), library))
                                except UnicodeEncodeError:
                                    self.warn(
                                        "Got unicode decode error on {} in {}".format(sch_device.get_name(), library))
                                    pass

    def check_supply_symbols(self):
        ground_dss = Swoop.From(self.sch).get_parts().filtered_by(lambda x: x.get_deviceset() in checker_options.ground_device_sets_names)
        grounds = ground_dss.get_name()

        # check rotated pwr/gnds
        rotated = Swoop.From(self.sch).get_sheets().get_instances().filtered_by(
            lambda x: x.get_part() in grounds).filtered_by(lambda x: not (x.get_rot() in [None, "R0"]))

        if len(rotated):
            if self.fix:
                rotated.set_rot("R0")
            else:
                self.warn(
                    "These ground symbols are oriented incorrectly. Grounds should point down: {}".format(
                        " ".join(map(lambda x: output_format(x, type='part'), rotated.get_part()))))

        power_dss = Swoop.From(self.sch).get_parts().filtered_by(
            lambda x: x.get_deviceset() in checker_options.power_device_set_names)
        powers = power_dss.get_name()

        rotated = Swoop.From(self.sch).get_sheets().get_instances().filtered_by(
            lambda x: x.get_part() in powers).filtered_by(lambda x: not (x.get_rot() in [None, "R0"]))

        if len(rotated):
            if self.fix:
                rotated.set_rot("R0")
            else:
                self.warn(
                    "These power symbols are oriented incorrectly. Power symbols should point up: {}".format(
                        " ".join(map(lambda x: output_format(x, type='part'), rotated.get_part()))))

        # Check for mismatch between symbols and nets
        for pr in Swoop.From(self.sch).get_sheets().get_nets().get_segments().get_pinrefs():
            part = self.sch.get_part(pr.get_part())

            if part.get_deviceset() in checker_options.ground_device_sets_names:
                net = pr.get_parent().get_parent()
                if pr.get_pin() != net.get_name():
                    self.warn("You have a {} ground symbol ({}) attached to {} intsead of {}.".format(part.get_deviceset(), output_format(part), output_format(net), pr.get_pin()))

            if part.get_deviceset() in checker_options.power_device_set_names:
                net = pr.get_parent().get_parent()
                if pr.get_pin() != net.get_name():
                    self.warn("You have a {} power symbol ({}) attached to {} instead of {}.".format(part.get_deviceset(), output_format(part), output_format(net), pr.get_pin()))


    def check_names(self):
        parts = Swoop.From(self.sch).get_parts().filtered_by(lambda x: "$" in x.get_name()).sort()
        if parts:
            self.warn(
                "These parts have '$' in their names.  Parts should all have nice, pretty names.  Either set the prefix on the device or name it yourself: {}".format(
                    " ".join(map(output_format, parts))), inexcusable=True)


        labeled_nets = Swoop.From(self.sch).get_sheets().get_nets().get_segments().get_labels().get_parent().get_parent().filtered_by(lambda x: '$' in x.get_name()).sort()

        if labeled_nets.count():
            self.warn(
                "These nets have labels on them and have '$' in their names.  Labeled nets should have meaningful names: {}".format(
                    " ".join(map(output_format, labeled_nets))), inexcusable=True)


        net_names = set(Swoop.From(self.sch).get_sheets().get_nets().get_name())
        part_names = set(Swoop.From(self.sch).get_parts().get_name())

        i = net_names.intersection(part_names)
        if i:
            self.warn("The following are names of both a net and part.  That's confusing: {}".format(", ".join(map(lambda x:"'{}'".format(x),i))), inexcusable=True)


    def check_nets(self):

        nets = Swoop.From(self.sch).get_sheets().get_nets()
        routed_wires = nets.get_segments().get_wires().with_layer("Nets")

        self.check_intersections(routed_wires)

        # Aligment.
        alignment = 25.4/10.0/4.0
        for w in routed_wires:
            with NestedError(self.errors, w):
                x1, y1, x2, y2 = w.get_points()

                if abs(x1 - x2) < 0.001 or abs(y1 - y2) < 0.001:
                    pass
                else:
                    self.warn(
                        "Net routed at odd angle: {} centered at ({}, {}) in layer {}".format(output_format(w.get_parent().get_parent()),
                                                                                              (x1 + x2) / 2,
                                                                                              (y1 + y2) / 2,
                                                                                              w.get_layer()), inexcusable=True)

                if not self.is_aligned(x1, alignment) or not self.is_aligned(y1, alignment):
                    if self.fix:
                        w.set_x1(math.ceil(x1 / alignment) * alignment)
                        w.set_y1(math.ceil(y1 / alignment) * alignment)
                    else:
                        self.warn(u"Segment of {} at ({}, {}) is not aligned {}\" grid".format(output_format(w.get_parent().get_parent()), x1, y1, alignment/25.4), inexcusable=True)

                if not self.is_aligned(x2, alignment) or not self.is_aligned(y2, alignment):
                    if self.fix:
                        w.set_x2(math.ceil(x2 / alignment) * alignment)
                        w.set_y2(math.ceil(y2 / alignment) * alignment)
                    else:
                        self.warn(u"Segment of {} at ({}, {}) is not aligned {}\" grid".format(output_format(w.get_parent().get_parent()), x2, y2, alignment/25.4), inexcusable=True)


        segments = nets.get_segments()
        for j in segments.get_junctions() + segments.get_labels():
            x1 = j.get_x()
            y1 = j.get_y()
            if not self.is_aligned(x1, alignment) or not self.is_aligned(y1, alignment):
                if self.fix:
                    j.set_x(math.ceil(x1 / alignment) * alignment)
                    j.set_y(math.ceil(y1 / alignment) * alignment)
                else:
                    self.warn(u"Junction or label at ({}, {}) is not aligned {}\" grid".format(x1, y1, alignment/25.4), inexcusable=True)

        # Check phantom connections
        point_list = {}
        for n in nets:
            points = set()
            wires = Swoop.From(n).get_segments().get_wires().with_layer("Nets")
            for w in wires:
                points.add((w.get_x1(), w.get_y1()))
                points.add((w.get_x2(), w.get_y2()))

            point_list[n.get_name()] = points

        _nets = list(enumerate(nets))

        for i, n1 in _nets:
            for j, n2 in filter(lambda x: x[0] > i, _nets):
                intersect = point_list[n1.get_name()].intersection(point_list[n2.get_name()])
                if len(intersect) > 0:
                    self.warn(u"Nets {} and {} have point in common but are not connected.  If you move them apart and back together they will probably connect.  Locations: {}".format(output_format(n1), output_format(n2), ", ".join(map(str, intersect))), inexcusable=True)

        # check that labels are on the nets the label
        for n in nets:
            # points = set()
            #
            # for w in Swoop.From(n).get_segments().get_wires().with_layer("Nets"):
            #     points.add((w.get_x1(), w.get_y1()))
            #     points.add((w.get_x2(), w.get_y2()))
            #
            # for i in Swoop.From(n).get_segments().get_labels():
            #     if (i.get_x(), i.get_y()) not in points:
            #         self.warn(u"Label of {} at {} is not on the net it labels.".format(output_format(n),
            #                                                                            (i.get_x(), i.get_y())))
            wires = Swoop.From(n).get_segments().get_wires().with_layer("Nets")

            for i in Swoop.From(n).get_segments().get_labels():
                found_match = False
                for w in wires:
                    if w.get_x1() == w.get_x2():
                        if i.get_x() == w.get_x1() and i.get_y() <= max(w.get_y1(), w.get_y2()) and i.get_y() >= min(w.get_y1(), w.get_y2()):
                            found_match = True
                            break
                    elif w.get_y1() == w.get_y2():
                        if i.get_y() == w.get_y1() and i.get_x() <= max(w.get_x1(), w.get_x2()) and i.get_x() >= min(w.get_x1(), w.get_x2()):
                            found_match = True
                            break
                    else:
                        pass # not vertical or horizontal.
                if not found_match:
                    self.warn(u"Label of {} at {} is not on the net it labels.".format(output_format(n),
                                                                                       (i.get_x(), i.get_y())), inexcusable=True)

        # check for single node nets.
        for n in nets:
            if Swoop.From(n).get_segments().get_pinrefs().count() in [0, 1]:
                self.warn("Net {} has zero or 1 pins.  You should probably delete it.".format(output_format(n)))


    def check_frame(self):
        if not Swoop.From(self.sch).get_parts().with_deviceset("FRAME_B_L"):
            self.warn(u"You don't have a frame around your schematic.")

        if Swoop.From(self.sch).get_sheets().get_plain_elements().with_layer("Info") < 5:
            self.warn(u"You don't have enough documentation (items in layer 'Info') on your schematic.  If your schematic is very simple, you can provide that as an explanation for why no documentation is needed.")

    def check_parts(self):

        # alignment
        alignment = 25.4/10/4
        for i in Swoop.From(self.sch).get_sheets().get_instances():

            x1 = i.get_x()
            y1 = i.get_y()
            if not self.is_aligned(x1, alignment) or not self.is_aligned(y1, alignment):
                if self.fix:
                    i.set_x(math.ceil(x1 / alignment) * alignment)
                    i.set_y(math.ceil(y1 / alignment) * alignment)
                else:
                    self.warn(
                        "{} not aligned to {}\" grid".format(output_format(i.find_part()), alignment/25.4), inexcusable=True)

        # check for mismatched values
        for p in Swoop.From(self.sch).get_parts():
            attribute = p.find_technology().get_attribute("VALUE")
            if attribute and attribute.get_value() != p.get_value():
                self.warn("Part {} has a pre-set value ({}) but you have set a different value ({}).  "
                          "This is probably an error, since the value won't match the part the device's "
                          "attributes describe.".format(p.get_name(),
                                                              attribute.get_value(),
                                                              p.get_value()))

        for p in Swoop.From(self.sch).get_parts():
            # The right solution here is to count the number of pins on the the part.  If there are only 1 or 0 pins, then its not an error if just 1 or 0 pins are connected.
            if Swoop.From(p).find_deviceset().get_gates().find_symbol().get_pins().count() not in [0,1]:# not in checker_options.power_and_ground_names + ["ANTENNA", "FRAME_B_L", "MOUNTING-HOLE"] and "VIA" not in p.get_deviceset():
                if Swoop.From(self.sch).get_sheets().get_nets().get_segments().get_pinrefs().filtered_by(lambda x: x.get_part() == p.get_name()).count() in [0, 1]:
                    self.warn("Part {} has 1 or zero nets attached.".format(output_format(p)))


    def do_check(self):
        if not self.sch:
            return

        with NestedError(self.errors, self.sch.get_filename()):
            self.check_supply_symbols()
            self.check_names()
            self.check_libraries()
            self.check_nets()
            self.check_frame()
            self.check_parts()
            LibraryLint(lbrs=Swoop.From(self.sch).get_libraries(), errors=self.errors, fix=self.fix, options=self.options).check()