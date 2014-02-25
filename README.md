trac-ldap-sync
==============

A script from syncing user information from LDAP to Trac.

This Python script is used to fill in the email address field in Trac based on 
information found from LDAP. The challenge is that Trac does not have a concept 
of user accounts: instead it stores the per-user information in session 
information. This script should not need many changes to be useful in other 
LDAP/Trac+postgresql environments.


PREQUISITES
===========

The script makes use of the following Python libraries:

- psycopg2
- ldap
- smtplib
- mail

Some of these are usually included in the distribution or easily installable 
using the package manager.

USAGE
=====

First copy "config/ldapsync.conf.example" to "config/ldapsync.conf" and edit the 
configuration to suit your environment.

If you want to do a dry-run first (recommended), either comment our the 
"conn.commit()" line in ldapsync.py or edit the "self.include" list in 
ldapsync.py to only include some usernames.

Next simply run the script with

  $ python ldapsync.py

If your configuration file is correct, you should get an email report telling 
which Trac users had their email address copied over from LDAP.

LICENSING
=========

This project is released under the BSD license (see file LICENSE for details).

This script uses of pieces of code from an older BSD-licensed "perftest" script, 
(C) 2011 OpenVPN Technologies, Inc. ConfigParser parts are to some extent (C) 
2008 Samuli Seppänen.
