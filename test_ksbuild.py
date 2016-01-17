#!/usr/bin/python

import unittest

import ksbuild


class TestKickstartBit(unittest.TestCase):
    def setUp(self):
        self.ks1 = ksbuild.KickstartBit("ks1", "graphical")
        self.ks2 = ksbuild.KickstartBit("ks2", "text")
        self.ks3 = ksbuild.KickstartBit("ks3", "autopart")
        self.ks4 = ksbuild.KickstartBit("ks4", "rootpw secret")
        self.ks5 = ksbuild.KickstartBit("ks5", "#;auth\n%packages\n@core")

    def test_conflicting_commands(self):
        expected = set(['cmdline', 'graphical', 'vnc', 'text'])
        self.assertEqual(self.ks1.conflicting_commands(), expected)

        self.assertEqual(self.ks5.conflicting_commands(), set(["auth", "%packages"]))

    def test_conflicts_with(self):
        self.assertTrue(self.ks1.conflicts_with(self.ks2))

    def test_merge(self):
        with self.assertRaises(ksbuild.MergeError):
            self.ks1.merge(self.ks2)

        self.ks3.merge(self.ks1)
        self.assertEqual(self.ks3.included_names(), ("ks3", "ks1"))
        with self.assertRaises(ksbuild.MergeError):
            self.ks3.merge(self.ks2)

        with self.assertRaises(ksbuild.MergeError):
            self.ks3.merge(self.ks1)

        str(self.ks4)
        with self.assertRaises(ksbuild.MergeError):
            self.ks4.merge(self.ks1)

    def test_included_names(self):
        self.ks1.merge(self.ks3)
        self.assertEqual(self.ks1.included_names(), ("ks1", "ks3"))
        self.assertEqual(self.ks2.included_names(), ("ks2",))

    def test_str(self):
        expected = """# ksbuild ks1
graphical

# ksbuild Mandatory
autopart
bootloader --location=mbr
clearpart --all --initlabel
keyboard us
lang en_US.UTF-8
network --bootproto dhcp
rootpw anaconda
selinux --enforcing
timezone America/New_York
zerombr

# ksbuild Mandatory
%packages --default
%end"""

        self.assertEqual(str(self.ks1), expected)

        self.ks2.merge(self.ks3)
        self.ks2.merge(self.ks4)
        self.ks2.merge(self.ks5)

        expected = """# ksbuild ks2
text

# ksbuild ks3
autopart

# ksbuild ks4
rootpw secret

# ksbuild ks5
#;auth

# ksbuild Mandatory
bootloader --location=mbr
clearpart --all --initlabel
keyboard us
lang en_US.UTF-8
network --bootproto dhcp
selinux --enforcing
timezone America/New_York
zerombr

# ksbuild ks5
%packages
@core"""

        self.assertEqual(str(self.ks2), expected)


class TestCommandsAndSectionFunc(unittest.TestCase):
    def test_commands_and_sections(self):
        commands, sections = ksbuild._commands_and_sections("ks1", "graphical\nautopart", True)
        self.assertEqual(commands, ["graphical", "autopart"])
        self.assertEqual(sections, [])

        commands, sections = ksbuild._commands_and_sections("ks1", "graphical\nautopart", False)
        self.assertEqual(commands, ["# ksbuild ks1", "graphical", "autopart"])
        self.assertEqual(sections, [])
        commands, sections = ksbuild._commands_and_sections("ks1", "#;part\ngraphical\nautopart", True)
        self.assertEqual(commands, ["#;part", "graphical", "autopart"])
        self.assertEqual(sections, [])


if __name__ == "__main__":
    unittest.main()
