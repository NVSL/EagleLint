import re
import Swoop
import copy
import SwoopChecker
from SwoopChecker import ErrorCollector, CheckSet
from LibraryStyle import LibraryLint
from BoardStyle import BoardLint
from SchematicStyle import SchematicLint
import zipfile
import importlib
import StringIO


def lint_lbr(errors, lbr, fix=False):
    LibraryLint(errors=errors, lbrs=[lbr.get_library()], fix=fix).check()

class UnimplementedException(Exception):
    pass;

GenericChecks = CheckSet([
    LibraryLint, BoardLint, SchematicLint
])

def get_checker(checker):
    try:
        return eval(checker)
    except:
        try:
            head = checker.split(".")[:-1]
            if not head:
                return eval(checker)
            tail = checker.split(".")[-1]
            m = importlib.import_module(".".join(head))
            return getattr(m,tail)
        except Exception as e:
            raise Exception("Couldn't load checker '{}': {}".format(checker, e))

def run_eaglelint_check(files,
               lints,
               errors = None,
               fix=False,
               write=None,
               ext=None,
               filter=False,
               options=None
               ):
    if options is None:
        options = {}

    if not errors:
        errors = ErrorCollector()

    schs = {}
    lbrs = {}
    brds = {}

    def collect_files(file_list, strict=True):
        for (filename, stream) in file_list.items():
            if filename[-3:] == "sch":
                sch = Swoop.SchematicFile.from_stream(Swoop.SchematicFile, stream, filename=filename)
                schs[filename] = sch
            elif filename[-3:] == "brd":
                brd = Swoop.BoardFile.from_stream(Swoop.BoardFile, stream, filename=filename)
                brds[filename] = brd
            elif filename[-3:] == "lbr":
                lbr = Swoop.LibraryFile.from_stream(Swoop.LibraryFile, stream, filename=filename)
                lbrs[filename] = lbr
            elif filename[-3:] == "zip":
                zip_contents = dict()
                zip = zipfile.ZipFile(stream)
                for i in zip.infolist():
                    full_path = "{}/{}".format(filename, i.filename)
                    if "__MACOSX" in full_path:
                        continue
                    with zip.open(i.filename) as zf:
                        contents = zf.read()
                        zip_contents[i.filename] = StringIO.StringIO(contents)
                collect_files(zip_contents, strict=False)
            elif strict:
                raise Exception("Illegal file type: {}".format(filename))
            else:
                pass

    collect_files(file_list=files)

    approved_errors = []
    if filter:
        for filename in files:
            try:
                with open(filename + ".err", "r") as f:
                    print("loading errors from {}".format(filename + ".err"))
                    for l in f.readlines():
                        l = l.strip()
                        m = re.search("(^|\(|:)([0-9A-F]{8})\)?$", l)
                        if m and m.group(2):
                            approved_errors.append(m.group(2))
            except IOError:
                pass

    brds_tmp = copy.deepcopy(brds)

    # Run paired .sch and .brd files together along with all the libraries.
    for sch in schs.values():
        brd_name = sch.get_filename()[:-3] + "brd"
        brd = brds.get(brd_name)
        if brd_name in brds_tmp:
            del brds_tmp[brd_name]
        for l in lints:
            get_checker(l)(sch=sch, errors=errors, brd=brd, lbrs=lbrs.values(), fix=fix, options=options).check()

    # Run unpained .brd files along with all the libraries
    for brd in brds_tmp.values():
        for l in lints:
            get_checker(l)(brd=brd, errors=errors, lbrs=lbrs.values(), fix=fix).check()

    # If there are no .sch and no .brd, run the libraries on their own.
    if len(schs) == 0 and len(brds) == 0:
        for l in lints:
            get_checker(l)(errors=errors, lbrs=lbrs.values(), fix=fix).check()

    if fix:

        for f in schs.values() + brds.values()+ lbrs.values():
            if not ext:
                n = ""
            else:
                n = "-" + ext

            base = f.get_filename()[:-4]
            suffix = f.get_filename()[-4:]
            name = base+n+suffix
            if write:
                f.write(name)

    errors.filter_by_hash(approved_errors)
    return errors

def main():
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Eagle lint")
    parser.add_argument("--sch", action='store_true', default=False, help="only run the schematic checks")
    parser.add_argument("--fix", action="store_true", help="Repair simple errors in a kludgy way")
    parser.add_argument("--no-filter", dest="filter", default=True, action="store_false", help="Don't filter errors")
    parser.add_argument("--write", action="store_true", help="Write out repaired files")
    parser.add_argument("--suffix", help="Write to foo-<suffix>.<ext> instead of foo.<ext>")
    parser.add_argument("--check", nargs="*", default=["GenericChecks"], help="Checkers to run")
    parser.add_argument("--strict", action="store_true", help="Warnings are errors")
    parser.add_argument("--quiet", action="store_true", help="Supress non-errors")
    parser.add_argument("--html", action="store_true", help="output html intsead of txt")
    parser.add_argument("--files", nargs="+", help="Files to lint")
    args = parser.parse_args()

    if not args.html:
        SwoopChecker.html_output = False

    files = {f: open(f, "r") for f in args.files}

    errors = run_eaglelint_check(files,
                        lints=args.check,
                        fix=args.fix,
                        write=args.write,
                        ext=args.suffix,
                        filter=args.filter)

    if not args.quiet:
        for e in filter(lambda x: x.level == "Info", errors.get_errors()):
            print(e)
    for e in filter(lambda x: x.level != "Info", errors.get_errors()):
        print(u"{}".format(e))

    if args.strict:
        if len(filter(lambda x: x.level != "Info", errors.get_errors())):
            sys.exit(1)
        else:
            sys.exit(0)

    else:
        if len(filter(lambda x: x.level == "Error", errors.get_errors())):
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()

