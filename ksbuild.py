#!/usr/bin/python


class MergeError(Exception): pass


class KickstartBit(object):
    def __init__(self, name, body, version=None, compact=False):
        self._included = []
        if name is not None:
            self._included.append(name)
        self._initial_body = body
        self._version = version
        self._compact = compact

        self._commands, self._sections = \
            _commands_and_sections(name, body, compact)

        self._changed = False
        self._rendered = False

    def conflicting_commands(self):
        "Returns set of commands conflicting with this bit"
        commands = []

        for line in self._commands:
            line = line.lstrip()
            if line[:1].isalpha():
                commands.append(line.split()[0])
            elif line.startswith("#;"):
                commands.append(line[2:].lstrip().split()[0])
        if self._has_packages():
            commands.append("%packages")

        for command in list(commands):
            commands.extend(_mutually_exclusive(command))
        return set(commands)

    def conflicts_with(self, other):
        "True if contains conflicting_commands"
        conflicts = self.conflicting_commands().intersection(
            other.conflicting_commands())

        return len(conflicts) > 0

    def merge(self, other):
        "Merges other bit"
        if self._rendered:
            raise MergeError("Already rendered")

        if self.conflicts_with(other):
            raise MergeError("Can't merge conflicting bit")

        common = set(self._included).intersection(set(other.included_names()))

        if len(common) > 0:
            raise MergeError("Already included bits '%'", tuple(common))

        if len(other._commands) > 0:
            if not self._compact:
                self._commands += ['']
            self._commands += other._commands
        if len(other._sections) > 0:
            if not self._compact:
                self._sections += ['']
            self._sections += other._sections
        self._included.extend(other.included_names())
        self._changed = True

    def included_names(self):
        "Returns list of included names"
        return tuple(self._included)

    def __str__(self):
        if not self._rendered:
            self._render()
        return self._body()

    def _has_packages(self):
        "True if %packages included"
        for line in self._sections:
            if line.lstrip().startswith("%packages"):
                return True

        return False

    def _render(self):
        required = _mandatory_bits(self._version)
        required = [ks for ks in required if not ks.conflicts_with(self)]
        if len(required) > 0:
            selected = required[0]
            for missing in required[1:]:
                selected.merge(missing)
            self.merge(KickstartBit("Mandatory", selected._body()))
        self._rendered = True

    def _body(self):
        if self._changed:
            text = ""
            if len(self._commands) > 0:
                text += "\n".join(self._commands)
            if len(self._sections) > 0:
                text += "\n%s" % "\n".join(self._sections)
        else:
            if not self._compact:
                text = "# ksbuild %s\n" % (tuple(self._included))
            text += self._initial_body
        return text


def build_kickstarts(bits):
    kickstarts = [bits[0]]
    for bit in bits[1:]:
        candidates = [ks for ks in kickstarts if not ks.conflicts_with(bit)]
        if len(candidates) == 0:
            kickstarts.append(bit)
        else:
            candidates[0].merge(bit)
    return kickstarts


def _commands_and_sections(name, body, compact):
    "Initial split into commands & sections"
    buf = []
    commands = []
    sections = []
    in_section = False
    for line in body.split("\n"):
        buf.append(line)
        trimmed = line.lstrip()
        if in_section and trimmed.startswith("%end"):
            in_section = False
            sections += buf
            buf = []
        elif in_section and trimmed.startswith("%"):
            sections += buf
            buf = []
        elif trimmed.startswith("%include"):
            commands += buf
            buf = []
        elif trimmed.startswith("%"):
            in_section = True
        elif in_section:
            pass
        elif trimmed[:1].isalpha():
            commands += buf
            buf = []
        elif trimmed.startswith("#;"):
            commands += buf
            buf = []

    if in_section:
        sections += buf

    if not compact:
        if len(commands) > 0:
            commands.insert(0, "# ksbuild %s" % name)
        if len(sections) > 0:
            sections.insert(0, "# ksbuild %s" % name)

    return (commands, sections)


def _mandatory_bits(version):
    mandatory = [
        "autopart",
        "bootloader --location=mbr",
        "clearpart --all --initlabel",
        "keyboard us",
        "lang en_US.UTF-8",
        "network --bootproto dhcp",
        "%packages --default\n%end",
        "rootpw anaconda",
        "selinux --enforcing",
        "timezone America/New_York",
        "zerombr"]
    return [KickstartBit(None, body, compact=True) for body in mandatory]


def _mutually_exclusive(command):
    groups = [
        ["cmdline", "graphical", "text", "vnc"],
        ["autopart", "logvol", "part", "raid", "volgroup"]]

    for group in groups:
        if command in group:
            return group
    return [command]
