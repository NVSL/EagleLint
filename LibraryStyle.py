from SwoopChecker import Checker, NestedError, checker_options, bounding_box_size, inch_to_mm, mm_to_inch

import Swoop

class LibraryLint(Checker):

    def __init__(self, *args, **kwargs):
        super(LibraryLint, self).__init__(*args, **kwargs)
        self.required_deviceset_attributes = ["CREATOR", "DIST", "DISTPN"]  # , "MFR", "MPN",
    def do_check(self):
        for library in self.lbrs:
            if isinstance(library, Swoop.LibraryFile):
                name = library.get_filename()
                library = library.get_library()
            else:
                name = library.get_name()

            if name in (self.options.get("skipped_lbrs") or []):
                return

            with NestedError(self.errors, name):
                self.info("Examined {}".format(name))
                fix = self.fix

                if fix:
                    for t in Swoop.From(library).get_devicesets().get_devices().get_technologies():
                        for attr in self.required_deviceset_attributes:
                            if not t.get_attribute(attr) or not t.get_attribute(attr).get_value():
                                t.add_attribute(Swoop.Attribute().set_name(attr).set_value("Unknown"))

                    for p in library.get_packages():
                        if not Swoop.From(p).get_drawing_elements().without_type(Swoop.Hole).with_layer("tKeepout").count():
                            p.add_drawing_element(Swoop.Wire().set_x1(0).set_y1(0).set_x2(0).set_y2(0).set_width(1).set_layer("tKeepout"))

                for s in Swoop.From(library).get_symbols():
                    self.check_symbol(s, checker_options.power_and_ground_names)

                for p in Swoop.From(library).get_packages():
                    self.check_package(p)

                for ds in Swoop.From(library).get_devicesets():
                    self.check_deviceset(ds, checker_options.power_and_ground_names)

    def check_symbol(self, s, power_and_ground):

        with NestedError(self.errors, s):
            for p in Swoop.From(s).get_pins():
                if "$" in p.get_name():
                    self.warn(u"Pin '{}' has '$' in name.  Give your pins nice names.".format(p.get_name()), inexcusable=True)

                with NestedError(self.errors, p):
                    if not self.is_aligned(p.get_x(), 2.54) or not self.is_aligned(p.get_y(), 2.54):
                        self.error(u"Pin {} is not aligned to the 0.1\" grid. ({}, {})".format(p.get_name(), p.get_x(), p.get_y()), inexcusable=True)

            if s.get_name() not in power_and_ground + checker_options.symbols_that_need_no_name:
                names = Swoop.From(s).get_drawing_elements().with_type(Swoop.Text).filtered_by(lambda x: x.get_text().upper() == ">NAME")

                if not names:
                    self.warn(u"Symbol is missing '>NAME'. Every schematic symbol needs a '>NAME' in layer 'Names' so the name of the part is visible in schematic.")
                elif not names.with_layer("Names"):
                    if self.fix:
                        names.set_layer("Names")
                    else:
                        self.warn(u"'>NAME' is in the wrong layer ('{}').  Should be in 'Names'.".format(", ".join(names.get_layer())), inexcusable=True)

            values = Swoop.From(s).get_drawing_elements().with_type(Swoop.Text).filtered_by(lambda x: x.get_text().upper() == str(">VALUE"))
            if values.without_layer("Values"):
                if self.fix:
                    values.set_layer("Values")
                else:
                    self.warn(u"'>VALUE' is in the wrong layer ('{}').  Should be in 'Values'.".format(", ".join(values.get_layer())), inexcusable=True)

            names = Swoop.From(s).get_drawing_elements().with_type(Swoop.Text).filtered_by(lambda x: x.get_text().upper() == ">NAME")

            if names.without_layer("Names"):
                if self.fix:
                    names.set_layer("Names")
                else:
                    self.warn(u"'>NAME' is in the wrong layer ('{}').  Should be in 'Names'.".format(", ".join(names.get_layer())), inexcusable=True)

                if not names.count():
                    self.warn(u"You should have '>NAME' in layer 'Names'.")

            if Swoop.From(s).get_drawing_elements().without_type(Swoop.Text).without_type(Swoop.Hole).with_layer(
                    "Info").count() > 0:
                self.warn(
                    u"You have some drawing in layer 'Info'. Usually drawings in symbols should go in layer 'Symbols'")



    def check_deviceset(self, ds, power_and_ground):
        with NestedError(self.errors, ds):
            gates = Swoop.From(ds).get_gates()

            if len(gates) == 1:
                if gates[0].get_x() != 0 or gates[0].get_y() != 0:
                    self.warn(u"In the left pane of the device window, the schematic symbol for device should be at origin (0,0) instead of ({} ,{}).".format(gates[0].get_x(),
                                                                                                       gates[
                                                                                                           0].get_y()), inexcusable=True)

            if ds.get_name() not in power_and_ground:
                if ds.get_uservalue():
                    if len(Swoop.From(ds).get_gates().find_symbol().get_drawing_elements().with_type(
                            Swoop.Text).with_text(lambda x: x.upper() == ">VALUE")) == 0:
                        self.warn(u"Device has user value (look for a check box at the bottom of the device editor window), but symbol does not include '>VALUE'.  This means the value will not visible in the schematic.")


            for device in ds.get_devices():
                value_labels = Swoop.From(device).find_package().get_drawing_elements().with_type(
                        Swoop.Text).with_text(lambda x: x.upper() == ">VALUE").count()

                if ds.get_uservalue() and value_labels == 0:
                    self.warn(u"Device has user value (look for a check box at the bottom of the device editor window), but package for variant '{}' does not include '>VALUE'.  This means the value will not be visible in the board.".format(device.get_name()))
                if not ds.get_uservalue() and value_labels > 0:
                    self.warn(u"Device does not have user value (look for a check box at the bottom of the device editor window), but package for variant '{}' includes '>VALUE'.  This means the package name will appear on the board, which is probably not what you want.".format(device.get_name()))

            for d in ds.get_devices():
                if d.get_package() is not None:
                    with NestedError(self.errors, d):
                        t = d.get_technology("")
                        if not t:
                            self.warn("{} does not have a default technology".format(d.get_name()))
                            continue
                        for a in self.required_deviceset_attributes:
                            if t.get_attribute(a) is None or not t.get_attribute(a).get_value():
                                self.warn(u"Missing required attribute '{}'".format(a), inexcusable=True)
                            elif not t.get_attribute(a).get_constant():
                                self.warn(u"Attribute '{}' should be constant.".format(a), inexcusable=True)

    def check_package(self, p):
        silkscreen_layers = ["tName", "bNames", "tPlace", "bPlace"]
        elements = Swoop.From(p).get_drawing_elements()
        with NestedError(self.errors, p):
            dims = Swoop.From(p).get_drawing_elements().with_type(Swoop.Dimension).with_layer("Dimension")
            if not all(dims.map(lambda x: x.get_width() >= 0.1)):
                self.error("Lines in layer 'Dimension' must be thicker than 0.1mm", inexcusable=True)

            if not elements.with_type(Swoop.Text).filtered_by(lambda x: x.get_text().upper() == ">NAME") and elements.count() < 200:  # this is a heuristic to skip graphics.  They have many, many drawing elements.
                self.warn(u"Package is missing '>NAME'.  Every package needs to a '>NAME' so the part's name will be visible on the board.".format(p.get_name()))

            for q in p.get_pads() + p.get_smds():
                if "$" in q.get_name():
                    self.warn(u"Pad/SMD '{}' has '$' in name.  Give your pads and SMDs nice names.".format(q.get_name()), inexcusable=True)

            for t in elements.with_type(Swoop.Text):
                if t.get_text().upper() == ">NAME" and t.get_layer() not in ["tNames", "bNames"]:  # , "tDocu", "bDocu"]:
                    if self.fix:
                        t.set_layer("tNames")
                    else:
                        self.warn(
                            u"'>NAME' in text object in layer {} instead of tNames or bNames".format(t.get_layer()))

                if t.get_text().upper() == ">VALUE" and t.get_layer() not in ["tValues", "bValues"]:  # , "tDocu", "bDocu"]:
                    if self.fix:
                        t.set_layer("tValues")
                    else:
                        self.warn(
                            u"'>VALUE' in text object in layer {} instead of tValues or bValues".format(t.get_layer()))

                if t.get_text().upper() in [">NAME", ">VALUE"] and (t.get_size() < checker_options.silkscreen_min_size or t.get_ratio() != checker_options.silkscreen_ratio or t.get_font() not in checker_options.silkscreen_fonts):
                    if self.fix:
                        t.set_size(checker_options.silkscreen_min_size).set_ratio(checker_options.silkscreen_ratio).set_font(checker_options.silkscreen_fonts[0])
                    else:
                        self.warn(
                            u"'{}' in text object has wrong geometry (size={}mm, ratio={}%, font={}).  Should be {}mm, {}%, and one of these fonts that will render properly on the board during manufacturing: {}.".format(
                                t.get_text(),
                                t.get_size(), t.get_ratio(), t.get_font(),
                                checker_options.silkscreen_min_size,
                                checker_options.silkscreen_ratio,
                                ", ".join(checker_options.silkscreen_fonts)), inexcusable=True)

                if t.get_layer() in ["tNames", "bNames"] and t.get_text().upper() != ">NAME":
                    self.warn(u"Layer {} should only contain text items with the '>NAME', found '{}'".format(t.get_layer(), t.get_text()), inexcusable=True)

                if t.get_layer() in ["tValues", "bValues"] and t.get_text().upper() != ">VALUE":
                    self.warn(u"Layer {} should only contain text items with '>VALUE', found '{}'".format(t.get_layer(), t.get_text()), inexcusable=True)

                if t.get_layer() in silkscreen_layers:

                    if t.get_size() < checker_options.silkscreen_min_size:
                        self.warn(u"Text '{}' in layer {} is too small ({}mm).  To be legible on the board it should be at least {}mm.".format(t.get_text(), t.get_layer(),
                                                                                     t.get_size(), checker_options.silkscreen_min_size), inexcusable=True)

                    if t.get_font() != "vector":
                        self.warn(u"Text '{}' in layer {} is not in the vector font.  The other fonts don't render properly on the board.".format(t.get_text(), t.get_layer()), inexcusable=True)

            if elements.without_type(Swoop.Hole).with_layer("tKeepout").count() == 0 and elements.count() < 50:
                self.error("Nothing in tKeepout.  All packages should include a keepout area to prevent parts from overlapping.")

            if elements.without_type(Swoop.Hole).with_layer("tPlace").count() == 0 and elements.count() < 50:
                self.error("Nothing in tPlace.  Packages should include lines or shapes showing how the part should be placed on the board.  For ICs this should precisely show the location of four courners of the part.  For polarized parts, it should illustrate the polarity.  For other parts a full or partial outline of the part is sufficient.")

            if "ANT" not in p.get_name() and "HOLE" not in p.get_name() and "BRIDGE" not in p.get_name() and "LAYER_LABELS" not in p.get_name():
                if elements.without_type(Swoop.Hole).with_layer("Top").count():
                    self.error(u"Wires found in Top layer.  You probably want an SMD instead.")
                if elements.without_type(Swoop.Hole).with_layer("Bottom").count():
                    self.error(u"Wires found in Bottom layer.  You probably want an SMD instead.")

            if Swoop.From(p).get_smds().with_layer("Bottom").count():
                self.warn(u"SMD found on bottom layer.  They should almost always be on 'Top'")

            tdocu = elements.without_type(Swoop.Hole).with_layer("tDocu")
            if tdocu.count() < 4 and tdocu.with_type(Swoop.Circle) == 0 and elements.count() < 50:
                self.warn("You should have box or circle in tDocu that matches the size of the package")