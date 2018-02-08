#!/usr/bin/python
# -*- coding: utf-8 -*-

from email.mime.text import MIMEText
import smtplib
import ldap
import psycopg2
import ConfigParser
import sys

class ldapsync():
    def __init__(self):

        config = ConfigParser.ConfigParser()
        filename = "/etc/trac-ldap-sync.conf"
        try:
            config.readfp(open(filename))
        except IOError:
            print "Missing configuration file ("+filename+")"
            print
            sys.exit(1)

        # Parse configuration file
        try:
            self.ldap_uri = config.get("ldap","ldap_uri")
            self.bind_dn = config.get("ldap","bind_dn")
            self.bind_pw = config.get("ldap","bind_pw")
            self.basedn = config.get("ldap","basedn")

            self.db_user = config.get("database","db_user")
            self.db_password = config.get("database","db_password")
            self.db_host = config.get("database","db_host")
            self.db_port = config.get("database","db_port")
            self.db_name = config.get("database","db_name")

            self.source = config.get("email","source")
            self.target = config.get("email","target")
            self.smtp_host = config.get("email","smtp_host")

        except:
            print "Error in "+filename+", please take a look at "+filename+".sample"
            sys.exit(1)

        # These can't easily be read from the config file
        self.scope = ldap.SCOPE_ONELEVEL
        self.auth_type = ldap.AUTH_SIMPLE

        # If this list is empty, include all users, otherwise do not modify 
        # users not listed here. Primarily useful for debugging and testing.
        self.include = []
        #self.include = ['samuli']

    def get_ldap_emails(self,users):
        """Feed in a set of usernames and get a username:email dictionary back from LDAP""" 

        self.l = ldap.initialize(self.ldap_uri)
        self.l.bind(self.bind_dn, self.bind_pw, self.auth_type)

        results={}

        for username in users:
            result = self.l.search_s(self.basedn,self.scope,'(cn='+username+')',['mail'])

            try:
                email=result[0][1]['mail'][0]
                results[username] = email
            except IndexError:
                email=None

        self.l.unbind()
        return results

    def get_db_users_without_email(self):
        """Get a list of usernames for authenticated sessions"""
        conn = psycopg2.connect(database=self.db_name, user=self.db_user, password=self.db_password, host=self.db_host, port=self.db_port)
        cur = conn.cursor()

        # Get all users, regardless of whether they have an email in Trac or not
        cur.execute("SELECT sid FROM session WHERE authenticated=1")

        auth_sessions=[]
        while True:
            try:
                # This list will have duplicate entries in it
                auth_sessions.append(cur.fetchone()[0])
            except TypeError:
                break

        # Eliminate duplicates
        all_users = set(auth_sessions)

        # Get those users which do have an email
        cur.execute("SELECT sid FROM session_attribute WHERE (name='email' AND authenticated=1)")

        arr = []
        while True:
            try:
                arr.append(cur.fetchone()[0])
            except TypeError:
                break

        # Eliminate duplicates (which should not exist)
        users_with_email = set(arr)

        # Get list of users without an email address
        users_without_email = set(all_users - users_with_email)

        cur.close()
        conn.close()
        return users_without_email

    def add_emails_from_ldap(self,users):
        """Add email addresses to Trac based on LDAP information"""

        # Get dictionary of username:email pairs from LDAP
        userdict=self.get_ldap_emails(users)

        conn = psycopg2.connect(database=self.db_name, user=self.db_user, password=self.db_password, host=self.db_host, port=self.db_port)
        cur = conn.cursor()

        # Add email addresses for the users based on LDAP information but _only 
        # if_ email address is missing from Trac
        changes=["Synced emails from LDAP for the following users: "]
        for user in users:
            if user in self.include or self.include == []:
                cur.execute("""INSERT INTO session_attribute (sid, authenticated, name, value) VALUES (%s, 1, 'email', %s);""", (user, userdict[user]))
                changes.append("    %s" % (user))

        # Only send an email report if changes were made
        if len(changes) > 1:
            self.email_report(changes)

        cur.close()
        conn.commit()
        conn.close()

    def email_report(self,changes):
        """Send a report of changes via email"""

        body = ""
        # Convert the list of changes to a string
        for change in changes:
            body = body + change + "\n"

        report = MIMEText(body)
        report['Subject'] = 'Trac LDAP email sync report'
        report['From'] = self.source
        report['To'] = self.target

        server = smtplib.SMTP(self.smtp_host)
        server.sendmail(self.source, [self.target], report.as_string())
        server.quit()


if __name__ == '__main__':

    sync = ldapsync()
    sync.add_emails_from_ldap(sync.get_db_users_without_email())
