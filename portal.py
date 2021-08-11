import base64

import numpy as np
from paypalrestsdk.notifications import WebhookEvent
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import *
import urllib.request
from werkzeug.utils import secure_filename
import requests
from flask_oidc import OpenIDConnect
from paypalrestsdk import BillingAgreement, configure
import pytz
from datetime import datetime
#import paypal_config_sandbox
import paypal_config
import sendgrid_api_key
import boto3
import pickle
import urllib.parse
from flask import Flask, flash, request, render_template, url_for, redirect, session, json

import mortgage
import user_layout
import free_version

from config import *

from index import application

dashboard_url = "https://rephi-dashboard.com"
user_portal_url = "https://rephi-dashboard.com/portal"

color_scheme_options = {"light": "Light",
                        "dark": "Dark",
                        "apex": "Apex"}

s3 = boto3.client('s3')

obj = s3.get_object(Bucket='refi-user-credentials',Key='accounts')
serializedObject = obj['Body'].read()
all_accounts = pickle.loads(serializedObject)

sg = SendGridAPIClient(sendgrid_api_key.SENDGRID_API_KEY)

# Initialize PayPal sdk
## Sandbox
#configure({
#    "mode": paypal_config_sandbox.MODE,
#    "client_id": paypal_config_sandbox.CLIENT_ID,
#    "client_secret": paypal_config_sandbox.CLIENT_SECRET
#})

# Live
configure({
    "mode": paypal_config.MODE,
    "client_id": paypal_config.CLIENT_ID,
    "client_secret": paypal_config.CLIENT_SECRET
})

oidc = OpenIDConnect(application)

def get_userinfo():
  obj = s3.get_object(Bucket='refi-user-credentials',Key='accounts')
  serializedObject = obj['Body'].read()
  all_accounts = pickle.loads(serializedObject)
  return all_accounts

def get_subscriptioninfo():
  obj = s3.get_object(Bucket='refi-user-credentials',Key='subscriptions')
  serializedObject = obj['Body'].read()
  subscriptions = pickle.loads(serializedObject)
  return subscriptions

def upload_userinfo(account_info):
  sd = pickle.dumps(account_info)
  s3.put_object(Bucket='refi-user-credentials',Key='accounts', Body=sd)

def upload_subscriptioninfo(subscription_info):
  sd = pickle.dumps(subscription_info)
  s3.put_object(Bucket='refi-user-credentials',Key='subscriptions', Body=sd)

def add_user(username, name, email, subscription_id=None, subscribed=False):
  all_accounts[username] = {
                            "subscribed": subscribed,
                            "subscription_id": subscription_id,
                            "individual_member": False,
                            "group_member": False,
                            "group_admin": False,
                            "scheme": "light",
                            "user_name": name,
                            "email": email,
                            "phone": "",
                            "title": "Loan Officer",
                            "company": "",
                            "nmls": "",
                            "address": "",
                            "city_state": "",
                            "org_nmls": "",
                            "headshot_url": "",
                            "company_logo_url": "",
                            "linkedin_url": "",
                            "facebook_url": "",
                            "twitter_url": "",
                            "include_fdic": True,
                            "include_ehl": True
                           }
  return all_accounts

def get_subscription_status(accounts, user, subscription_id=None):
  subscription = {
                   "account_holder_email": accounts[user]["email"],
                   "account_holder_name": accounts[user]["user_name"],
                   "active": False,
                   "seats": 0,
                   "agreement": None,
                   "individual": True,
                   "group_admin": False,
                   "group_user": False,
                   "paid_user": True
                 }
  if subscription_id == None:
    subscription_id = accounts[user]["subscription_id"]
  if subscription_id == None:
    subscription["active"] = False
    subscription["seats"] = 0
    subscription["agreement"] = {
                                  "State": "Inactive",
                                  "Description": "N/A",
                                  "Start date": "N/A",
                                  "Next billing date": "N/A"
                                }
    subscription["paid_user"] = True
  if subscription_id == "FREE_USER":
    subscription["active"] = True
    subscription["seats"] = 1
    subscription["agreement"] = {
                                  "State": "Active",
                                  "Description": "Free user account",
                                  "Start date": "N/A",
                                  "Next billing date": "N/A"
                                }
    subscription["paid_user"] = False
  else:
    billing_agreement = BillingAgreement.find(subscription_id)
    if "state" in billing_agreement:
      subscription["account_holder_email"] = billing_agreement["payer"]["payer_info"]["email"]
      subscription["account_holder_name"] = "%s %s"%(billing_agreement["payer"]["payer_info"]["first_name"],
                                                     billing_agreement["payer"]["payer_info"]["last_name"])
      state = billing_agreement["state"]
      if state == "Active":
        subscription["active"] = True
      if subscription["active"]:
        if billing_agreement["description"] == "Individual Plan":
          subscription["seats"] = 1
        elif billing_agreement["description"] == "10 User Group Plan":
          subscription["seats"] = 10
          subscription["individual"] = False
          if accounts[user]["group_admin"]:
            subscription["group_admin"] = True
          else:
            if not accounts[user]["subscribed"]:
              subscription["active"] = False
            subscription["group_user"] = True
        elif billing_agreement["description"] == "25 User Group Plan":
          subscription["seats"] = 25
          subscription["individual"] = False
          if accounts[user]["group_admin"]:
            subscription["group_admin"] = True
          else:
            if not accounts[user]["subscribed"]:
              subscription["active"] = False
            subscription["group_user"] = True
        start_date = datetime.strptime(billing_agreement["start_date"], '%Y-%m-%dT%H:%M:%SZ')
        next_date = datetime.strptime(billing_agreement["agreement_details"]["next_billing_date"], '%Y-%m-%dT%H:%M:%SZ')
        subscription["agreement"] = {
                                      "State": billing_agreement["state"],
                                      "Description": billing_agreement["description"],
                                      "Start date": start_date.strftime("%B %d, %Y %H:%M:%SZ"),
                                      "Next billing date": next_date.strftime("%B %d, %Y %H:%M:%SZ")
                                    }
        subscription["paid_user"] = True
    else:
      subscription["active"] = False
  return subscription

#@application.route("/")
#def dashboard():
#    print("Here")
#    layout = free_version.gen_free_version()
#    return layout.index()

@application.route("/portal")
@application.route("/portal/")
def portal():
    template = None
    info = None
    logged_in = True
    subscribed = False
    status = {
               "account_holder_email": None,
               "account_holder_name": None,
               "active": False,
               "seats": 0,
               "agreement": None,
               "individual": True,
               "group_admin": False,
               "group_user": False,
               "paid_user": True
             }

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      if not username in all_accounts:
        all_accounts = add_user(username, info["name"], info["email"])
        all_accounts[username]["individual_member"] = True
        upload_userinfo(all_accounts)
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])
      if status["active"]:
        unique_url = "%s%s"%(dashboard_url,username.replace("%40","@"))
        template = render_template("portal.html", profile=info, oidc=oidc, subscription=status, unique_url=unique_url)
      else:
        template = render_template("portal.html", profile=info, oidc=oidc, subscription=status)
    else:
      template = render_template("portal.html", profile=info, oidc=oidc, subscription=status)

    return template

@application.route("/paypal", methods=["POST"])
@application.route("/paypal/", methods=["POST"])
def paypal_webhook_handler():
  all_accounts = get_userinfo()

  headers = request.headers
  event_body = request.data
  req_data = request.json
  transmission_id = headers["Paypal-Transmission-Id"]
  timestamp = headers["Paypal-Transmission-Time"]
  webhook_id = "13X07775871854641"
  actual_signature = headers["Paypal-Transmission-Sig"]
  cert_url = headers["Paypal-Cert-Url"]
  auth_algo = headers["Paypal-Auth-Algo"]

  #sandbox_server = "https://ipnpb.sandbox.paypal.com/cgi-bin/webscr"
  #live_server = "https://ipnpb.paypal.com/cgi-bin/webscr"

  response = WebhookEvent.verify(
      transmission_id, timestamp, webhook_id, event_body.decode('utf-8'), cert_url, actual_signature, auth_algo)

  if True:
    if "state" in req_data["resource"]:
      if str(req_data["resource"]["state"]).lower() == "cancelled":
        try:
          mail = Mail()
          mail.from_email = "rephi@apexoptim.com"
          mail.template_id = "d-a71bd2a4f2c341d1b6dbba8ca3dbcb86"
          p = Personalization()
          p.add_to(Email(req_data["resource"]["payer"]["payer_info"]["email"]))
          mail.add_personalization(p)
          response = sg.send(mail)
        except Exception as e:
          print(e)
    elif "status" in req_data["resource"]:
      if str(req_data["resource"]["status"]).lower() == "cancelled":
        try:
          mail = Mail()
          mail.from_email = "rephi@apexoptim.com"
          mail.template_id = "d-a71bd2a4f2c341d1b6dbba8ca3dbcb86"
          p = Personalization()
          p.add_to(Email(req_data["resource"]["payer"]["payer_info"]["email"]))
          mail.add_personalization(p)
          response = sg.send(mail)
        except Exception as e:
          print(e)

    #subscription_id = req_data["resource"]["billing_info"]["id"]
    subscription_id = req_data["resource"]["id"]
    billing_agreement = BillingAgreement.find(subscription_id)
    if "state" in billing_agreement:
      state = billing_agreement["state"]
      for user in all_accounts:
        if all_accounts[user]["subscription_id"] == subscription_id:
          if state == "Active":
            all_accounts[user]["subscribed"] = True
          else:
            all_accounts[user]["subscribed"] = False
      upload_userinfo(all_accounts)
      
  return "OK"

@application.route("/paypal-transaction-complete", methods=["POST"])
@application.route("/paypal-transaction-complete/", methods=["POST"])
def paypal_transaction_complete():
  template = None
  info = None
  logged_in = True
  subscribed = False

  try:
    info = oidc.user_getinfo(["sub", "name", "email", "locale"])
  except:
    logged_in = False

  if logged_in:
    all_accounts = get_userinfo()

    req_data = request.json

    orderID = req_data["orderID"]
    subscriptionID = req_data["subscriptionID"]
    subscriptionType = req_data["subscriptionType"]

    username = "/"+urllib.parse.quote(info["email"])
    ## Always add user (whether they existed or not) so a new subscription overwrites the old data
    #if not username in all_accounts:
    all_accounts = add_user(username, info["name"], info["email"], subscriptionID, True)

    all_accounts[username]["order_id"] = orderID
    all_accounts[username]["subscription_id"] = subscriptionID
    all_accounts[username]["subscribed"] = True
    all_accounts[username]["subscription_type"] = subscriptionType
    if subscriptionType == "individual":
      all_accounts[username]["individual_member"] = True
    else:
      all_accounts[username]["group_admin"] = True
      all_accounts[username]["nactive_users"] = 0
      all_accounts[username]["active_users"] = [False for n in range(nusers)]
      all_accounts[username]["active_user_emails"] = ["" for n in range(nusers)]
      all_accounts[username]["active_user_names"] = ["" for n in range(nusers)]

    try:
      mail = Mail()
      mail.from_email = "rephi@apexoptim.com"
      mail.template_id = "d-415cf3ed643b429cb7eb0cb1e2fcd2f8"
      p = Personalization()
      p.add_to(Email(info["email"]))
      mail.add_personalization(p)
      response = sg.send(mail)
    except Exception as e:
      print(e)

    upload_userinfo(all_accounts)
      
  return "OK"

@application.route("/subscribe-success")
@application.route("/subscribe-success/")
def successful_subscribe():
    template = None
    info = None
    logged_in = True
    subscribed = False

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])
        
      if not all_accounts[username]["subscription_id"] == "None":
        billing_agreement = BillingAgreement.find(all_accounts[username]["subscription_id"])
        #print("\n"+str(billing_agreement.to_dict())+"\n")
        details = {
                    "plan_name": billing_agreement["description"],
                    "state": billing_agreement["state"],
                    "subscription_id": all_accounts[username]["subscription_id"],
                    "order_id": all_accounts[username]["order_id"],
                  }

        template = render_template("subscribe-success.html", profile=info, oidc=oidc, subscription=status, subscription_info=details)
      else:
        unique_url = "%s%s"%(dashboard_url,username.replace("%40","@"))
        template = render_template("portal.html", profile=info, oidc=oidc, subscription=status, unique_url=unique_url)
    else:
      template = redirect(url_for("login"))

    return template

@application.route("/subscribe", methods=["GET", "POST"])
@application.route("/subscribe/", methods=["GET", "POST"])
def subscribe():
    template = None
    info = None
    logged_in = True
    subscribed = False
    status = {
               "account_holder_email": None,
               "account_holder_name": None,
               "active": False,
               "seats": 0,
               "agreement": None,
               "individual": True,
               "group_admin": False,
               "group_user": False,
               "paid_user": True
             }

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()

      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])
      if request.method == "GET":
        if not status["active"]:
          template = render_template("subscribe.html", profile=info, oidc=oidc, subscription=status)
        else:
          template = render_template("subscription.html", profile=info, oidc=oidc, subscription=status, agreement=status["agreement"], paid_user=status["paid_user"])
      else:
        if request.form["action"] == "free":
          template = redirect("https://rephi-dashboard.com")
        if request.form["action"] == "individual":
          template = render_template("subscribe-individual.html", profile=info, oidc=oidc, subscription=status)
        elif request.form["action"] == "10user":
          template = render_template("subscribe-10user.html", profile=info, oidc=oidc, subscription=status)
        elif request.form["action"] == "25user":
          template = render_template("subscribe-25user.html", profile=info, oidc=oidc, subscription=status)
    else:
      if request.method == "GET":
        #template = redirect(url_for("login"))
        template = render_template("subscribe.html", profile=info, oidc=oidc, subscription=status)
      else:
        if request.form["action"] == "free":
          template = redirect("https://rephi-dashboard.com")
        else:
          template = redirect(url_for("login"))

    return template

@application.route("/subscription")
@application.route("/subscription/")
def subscription():
    template = None
    info = None
    logged_in = True
    subscribed = False

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])
      if not status["active"]:
        template = render_template("subscribe.html", profile=info, oidc=oidc, subscription=status)
      else:
        template = render_template("subscription.html", profile=info, oidc=oidc, subscription=status, agreement=status["agreement"])
    else:
      template = redirect(url_for("login"))

    return template

@application.route("/login")
@application.route("/login/")
def login():
    template = None
    info = None
    logged_in = True
    subscribed = False
    status = {
               "account_holder_email": None,
               "account_holder_name": None,
               "active": False,
               "seats": 0,
               "agreement": None,
               "individual": True,
               "group_admin": False,
               "group_user": False,
               "paid_user": True
             }

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])

      if username in all_accounts:
        unique_url = "%s%s"%(dashboard_url,username.replace("%40","@"))
        template = render_template("portal.html", profile=info, oidc=oidc, subscription=status, unique_url=unique_url)
    else:
      bu = oidc.client_secrets['issuer'].split('/oauth2')[0]
      cid = oidc.client_secrets['client_id']

      destination = '%s/'%(user_portal_url)
      state = {
          'csrf_token': session['oidc_csrf_token'],
          'destination': oidc.extra_data_serializer.dumps(destination).decode('utf-8')
      }

      template = render_template("login.html", oidc=oidc, subscription=status, baseUri=bu, clientId=cid, state=base64_to_str(state))

    return template


@application.route("/profile")
@application.route("/profile/")
def profile():
    template = None
    info = None
    logged_in = True
    subscribed = False

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])

      if not username in all_accounts:
        all_accounts = add_user(username, info["name"], info["email"])
        all_accounts[username]["individual_member"] = True
        upload_userinfo(all_accounts)

      if status["active"]:
        user_info = {"Color scheme": all_accounts[username]["scheme"].title(),
                     "Name": all_accounts[username]["user_name"],
                     "Title": all_accounts[username]["title"],
                     "Email": all_accounts[username]["email"],
                     "Phone": all_accounts[username]["phone"],
                     "Company": all_accounts[username]["company"],
                     "NMLS": all_accounts[username]["nmls"],
                     "Address": all_accounts[username]["address"],
                     "City/State/Zip": all_accounts[username]["city_state"],
                     "Organization NMLS": all_accounts[username]["org_nmls"],
                     "LinkedIn": all_accounts[username]["linkedin_url"],
                     "Twitter": all_accounts[username]["twitter_url"],
                     "Facebook": all_accounts[username]["facebook_url"]}
        img_urls = {"Headshot Url": all_accounts[username]["headshot_url"],
                    "Company Logo Url": all_accounts[username]["company_logo_url"]}
        org_logos = {"include_fdic": all_accounts[username]["include_fdic"],
                     "include_ehl": all_accounts[username]["include_ehl"]}
        disclaimer_info = ""
        if "disclaimers" in all_accounts[username]:
          disclaimer_info = all_accounts[username]["disclaimers"]

        template = render_template("profile.html", profile=info, oidc=oidc, subscription=status, user_info=user_info, img_urls=img_urls, org_logos=org_logos, disclaimer_info=disclaimer_info)
      else:
        template = render_template("portal.html", profile=info, oidc=oidc, subscription=status)
    else:
      template = redirect(url_for("login"))

    return template

@application.route("/manage-users", methods=["GET", "POST"])
@application.route("/manage-users/", methods=["GET", "POST"])
def manage_users():
    template = None
    info = None
    logged_in = True
    subscribed = False

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])
      if status["active"]:
        if all_accounts[username]["group_admin"]:
          nusers = status["seats"]
          if not "nactive_users" in all_accounts[username]:
            all_accounts[username]["nactive_users"] = 0
          if not "active_users" in all_accounts[username]:
            all_accounts[username]["active_users"] = [False for n in range(nusers)]
          if not "active_user_emails" in all_accounts[username]:
            all_accounts[username]["active_user_emails"] = ["" for n in range(nusers)]
          if not "active_user_names" in all_accounts[username]:
            all_accounts[username]["active_user_names"] = ["" for n in range(nusers)]
          upload_userinfo(all_accounts)
          all_accounts = get_userinfo()
          for n in range(nusers):
            if all_accounts[username]["active_users"][n]:
              all_accounts[username]["nactive_users"] += 1

          if request.method == "GET":
            template = render_template("manage-users.html", profile=info, oidc=oidc, subscription=status, 
                                       nusers = nusers, 
                                       nactive_users = all_accounts[username]["nactive_users"],
                                       active = all_accounts[username]["active_users"], 
                                       email = all_accounts[username]["active_user_emails"], 
                                       name = all_accounts[username]["active_user_names"])
          elif request.method == "POST":
            all_accounts[username]["nactive_users"] = 0
            for n in range(nusers):
              if request.form.get("active%d"%(n)) and not request.form["email%d"%(n)] == "" and not request.form["name%d"%(n)] == "":
                all_accounts[username]["active_users"][n] = True
                all_accounts[username]["nactive_users"] += 1
              else:
                all_accounts[username]["active_users"][n] = False
              all_accounts[username]["active_user_emails"][n] = request.form["email%d"%(n)] 
              all_accounts[username]["active_user_names"][n] = request.form["name%d"%(n)] 
            for n in range(nusers):
              if not all_accounts[username]["active_user_emails"][n] == "":
                user_to_add = "/"+urllib.parse.quote(all_accounts[username]["active_user_emails"][n])
                if user_to_add == username:
                  flash("Admin account comes with an included dashboard. No need to add as a user")
                  all_accounts[username]["active_users"][n] = False
                  all_accounts[username]["nactive_users"] -= 1
                  all_accounts[username]["active_user_names"][n] = ""
                  all_accounts[username]["active_user_emails"][n] = ""
                else:
                  if all_accounts[username]["active_users"][n]:
                    new = True
                    add = True
                    if user_to_add in all_accounts:
                      new = False
                      if "subscription_id" in all_accounts[user_to_add]:
                        new_user_sub = get_subscription_status(all_accounts,
                                                               user_to_add)
                        # Dont add user to group if the user already has their own subscription
                        if new_user_sub["active"] and not all_accounts[user_to_add]["subscription_id"] == all_accounts[username]["subscription_id"]:
                          if not all_accounts[user_to_add]["subscription_id"] == None:
                            all_accounts[username]["active_users"][n] = False
                            flash("%s already has an account with Rephi"%(user_to_add))
                            add = False
                    if add:
                      if new:
                        all_accounts = add_user(user_to_add, all_accounts[username]["active_user_names"][n], 
                                                             all_accounts[username]["active_user_emails"][n],
                                                             all_accounts[username]["subscription_id"], True)
                      else:
                        all_accounts[user_to_add]["subscribed"] = True
                        all_accounts[user_to_add]["subscription_id"] = all_accounts[username]["subscription_id"]
                      all_accounts[user_to_add]["group_member"] = True
                  else:
                    if all_accounts[user_to_add]["subscription_id"] == all_accounts[username]["subscription_id"]:
                      all_accounts[user_to_add]["subscribed"] = False
            upload_userinfo(all_accounts)
            template = render_template("manage-users.html", profile=info, oidc=oidc, subscription=status, 
                                       nusers=nusers, 
                                       nactive_users = all_accounts[username]["nactive_users"],
                                       active=all_accounts[username]["active_users"], 
                                       email=all_accounts[username]["active_user_emails"], 
                                       name=all_accounts[username]["active_user_names"])
        else:
          template = render_template("portal.html", profile=info, oidc=oidc, subscription=status)
      else:
        template = render_template("portal.html", profile=info, oidc=oidc, subscription=status)
    else:
      template = redirect(url_for("login"))
    return template

@application.route("/edit-client-parameters", methods=["GET", "POST"])
@application.route("/edit-client-parameters/", methods=["GET", "POST"])
def edit_client_parameters():
    template = None
    info = None
    logged_in = True
    subscribed = False

    # These are the rates available in the dropdown menu on the dashboard.
    #  They range from 1% to 10%
    available_rates = [0.01,0.01125,0.0125,0.01375,0.015,0.01625,0.0175,
                       0.01875,0.02,0.02125,0.0225,0.02375,0.025,0.02625,
                       0.0275,0.02875,0.03,0.03125,0.0325,0.03375,0.035,
                       0.03625,0.0375,0.03875,0.04,0.04125,0.0425,0.04375,
                       0.045,0.04625,0.0475,0.04875,0.05,0.05125,0.0525,0.05375,
                       0.055,0.05625,0.0575,0.05875,0.06,0.06125,0.0625,0.06375,
                       0.065,0.06625,0.0675,0.06875,0.07,0.07125,0.0725,0.07375,
                       0.075,0.07625,0.0775,0.07875,0.08,0.08125,0.0825,0.08375,
                       0.085,0.08625,0.0875,0.08875,0.09,0.09125,0.0925,0.09375,
                       0.095,0.09625,0.0975,0.09875,0.1]

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])
      if status["active"]:
        if request.method == "POST":
          input_names = ["principal", "interest_rate", "term", "extra_principal",
                         "start_month", "start_year", "refi_amount", "closing_costs",
                         "refi_interest_rate", "refi_term", "refi_month", "refi_year"]
          user_input = ["" for n in range(12)]
          user_input[0] = request.form["p-input"]
          user_input[1] = request.form["ir-input"]
          user_input[2] = request.form["t-input"]
          user_input[3] = request.form["ep-input"]
          user_input[4] = request.form["startmonth-input"]
          user_input[5] = request.form["startyear-input"]
          user_input[6] = request.form["rp-input"]
          user_input[7] = request.form["cc-input"]
          user_input[8] = request.form["rr-input"]
          user_input[9] = request.form["rt-input"]
          user_input[10] = request.form["refimonth-input"]
          user_input[11] = request.form["refiyear-input"]

          if not user_input[1] == "":
            binned_ir = np.digitize(np.array([float(user_input[1])]), available_rates)[0]
            if binned_ir == 0:
              user_input[1] = str(available_rates[binned_ir])
            else:
              user_input[1] = str(available_rates[binned_ir-1])
          if not user_input[8] == "":
            binned_rir = np.digitize(np.array([float(user_input[8])]), available_rates)[0]
            if binned_rir == 0:
              user_input[8] = str(available_rates[binned_rir])
            else:
              user_input[8] = str(available_rates[binned_rir-1])

          prefill = "%s%s?"%(dashboard_url, username.replace("%40","@"))
          for n in range(len(user_input)):
            if not user_input[n] == "":
              prefill += "%s=%s&"%(input_names[n],user_input[n])
          prefill = prefill[:-1]

          template = render_template("client-parameters.html", profile=info, oidc=oidc, subscription=status, prefill=prefill)
        else:
          template = render_template("edit-client-parameters.html", profile=info, oidc=oidc, subscription=status)
      else:
        template = render_template("portal.html", profile=info, oidc=oidc, subscription=status)
    else:
      template = redirect(url_for("login"))

    return template

@application.route("/edit-profile", methods=["GET", "POST"])
@application.route("/edit-profile/", methods=["GET", "POST"])
def edit_profile():
    template = None
    info = None
    logged_in = True
    subscribed = False

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])

      if status["active"]:
        if request.method == "POST":
          scheme_input = request.form["Color scheme-input"]
          name_input = request.form["Name-input"]
          title_input = request.form["Title-input"]
          email_input = request.form["Email-input"]
          phone_input = request.form["Phone-input"]
          company_input = request.form["Company-input"]
          nmls_input = request.form["NMLS-input"]
          address_input = request.form["Address-input"]
          csz_input = request.form["City/State/Zip-input"]
          org_nmls_input = request.form["Organization NMLS-input"]
          linkedin_input = request.form["LinkedIn-input"]
          twitter_input = request.form["Twitter-input"]
          facebook_input = request.form["Facebook-input"]
          include_fdic = request.form.get("fdic")
          include_ehl = request.form.get("ehl")
          disclaimers = request.form.get("disclaimers")
          if include_fdic == None:
            include_fdic = False
          else:
            include_fdic = True
          if include_ehl == None:
            include_ehl = False
          else:
            include_ehl = True
          if not "http://" in linkedin_input and not "https://" in linkedin_input:
            linkedin_input = "http://%s"%(linkedin_input)
          if not "http://" in twitter_input and not "https://" in twitter_input:
            twitter_input = "http://%s"%(twitter_input)
          if not "http://" in facebook_input and not "https://" in facebook_input:
            facebook_input = "http://%s"%(facebook_input)
          headshot = request.files["Headshot Url-input"]
          company_logo = request.files["Company Logo Url-input"]

          all_accounts[username]["scheme"] = scheme_input.lower()
          all_accounts[username]["user_name"] = name_input
          all_accounts[username]["title"] = title_input
          all_accounts[username]["email"] = email_input
          all_accounts[username]["phone"] = phone_input
          all_accounts[username]["company"] = company_input
          all_accounts[username]["nmls"] = nmls_input
          all_accounts[username]["address"] = address_input
          all_accounts[username]["city_state"] = csz_input
          all_accounts[username]["org_nmls"] = org_nmls_input
          all_accounts[username]["include_fdic"] = include_fdic
          all_accounts[username]["include_ehl"] = include_ehl
          all_accounts[username]["linkedin_url"] = linkedin_input
          all_accounts[username]["twitter_url"] = twitter_input
          all_accounts[username]["facebook_url"] = facebook_input
          all_accounts[username]["disclaimers"] = disclaimers
          if not headshot.filename == "":
            hs = "%s%s"%(username[1:],headshot.filename)
            hs_fs = secure_filename(hs)
            hs_name = "uploads/%s"%(hs_fs)
            headshot.save(hs_name)
            s3.upload_file(hs_name, "refi-user-images", "%s"%(hs_fs))
            all_accounts[username]["headshot_url"] = "https://refi-user-images.s3.amazonaws.com/%s"%(hs_fs)
          if not company_logo.filename == "":
            cl = "%s%s"%(username[1:],company_logo.filename)
            cl_fs = secure_filename(cl)
            cl_name = "uploads/%s"%(cl_fs)
            company_logo.save(cl_name)
            s3.upload_file(cl_name, "refi-user-images", "%s"%(cl_fs))
            all_accounts[username]["company_logo_url"] = "https://refi-user-images.s3.amazonaws.com/%s"%(cl_fs)

          upload_userinfo(all_accounts)

          user_info = {"Color scheme": all_accounts[username]["scheme"].title(),
                       "Name": all_accounts[username]["user_name"],
                       "Title": all_accounts[username]["title"],
                       "Email": all_accounts[username]["email"],
                       "Phone": all_accounts[username]["phone"],
                       "Company": all_accounts[username]["company"],
                       "NMLS": all_accounts[username]["nmls"],
                       "Address": all_accounts[username]["address"],
                       "City/State/Zip": all_accounts[username]["city_state"],
                       "Organization NMLS": all_accounts[username]["org_nmls"],
                       "LinkedIn": all_accounts[username]["linkedin_url"],
                       "Twitter": all_accounts[username]["twitter_url"],
                       "Facebook": all_accounts[username]["facebook_url"]}
          img_urls = {"Headshot Url": all_accounts[username]["headshot_url"],
                      "Company Logo Url": all_accounts[username]["company_logo_url"]}
          org_logos = {"include_fdic": all_accounts[username]["include_fdic"],
                       "include_ehl": all_accounts[username]["include_ehl"]}
          disclaimer_info = disclaimers

          template = render_template("profile.html", profile=info, oidc=oidc, subscription=status, user_info=user_info, img_urls=img_urls, org_logos=org_logos, disclaimer_info=disclaimer_info)
        else:
          if not username in all_accounts:
            all_accounts = add_user(username, info["name"], info["email"])
            all_accounts[username]["individual_member"] = True
            upload_userinfo(all_accounts)

          if status["active"]:
            subscribed = True
            user_info = {"Color scheme": all_accounts[username]["scheme"].title(),
                         "Name": all_accounts[username]["user_name"],
                         "Title": all_accounts[username]["title"],
                         "Email": all_accounts[username]["email"],
                         "Phone": all_accounts[username]["phone"],
                         "Company": all_accounts[username]["company"],
                         "NMLS": all_accounts[username]["nmls"],
                         "Address": all_accounts[username]["address"],
                         "City/State/Zip": all_accounts[username]["city_state"],
                         "Organization NMLS": all_accounts[username]["org_nmls"],
                         "LinkedIn": all_accounts[username]["linkedin_url"],
                         "Twitter": all_accounts[username]["twitter_url"],
                         "Facebook": all_accounts[username]["facebook_url"]}
            img_urls = {"Headshot Url": all_accounts[username]["headshot_url"],
                        "Company Logo Url": all_accounts[username]["company_logo_url"]}
            org_logos = {"include_fdic": all_accounts[username]["include_fdic"],
                         "include_ehl": all_accounts[username]["include_ehl"]}
            disclaimer_info = ""
            if "disclaimers" in all_accounts[username]:
              disclaimer_info = all_accounts[username]["disclaimers"]

            template = render_template("edit-profile.html", profile=info, oidc=oidc, subscription=status, user_info=user_info, img_urls=img_urls, color_scheme_options=color_scheme_options, org_logos=org_logos, disclaimer_info=disclaimer_info)
      else:
        template = render_template("portal.html", profile=info, oidc=oidc, subscription=status)
    else:
      template = redirect(url_for("login"))

    return template

@application.route("/cancel-success", methods=["GET", "POST"])
@application.route("/cancel-success/", methods=["GET", "POST"])
def cancel_success():
    template = None
    info = None
    logged_in = True
    subscribed = False

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      template = render_template("cancel-success.html", profile=info, oidc=oidc)
    else:
      template = redirect(url_for("login"))

    return template

@application.route("/cancel-failed", methods=["GET", "POST"])
@application.route("/cancel-failed/", methods=["GET", "POST"])
def cancel_failed():
    template = None
    info = None
    logged_in = True
    subscribed = False

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      template = render_template("cancel-failed.html", profile=info, oidc=oidc)
    else:
      template = redirect(url_for("login"))

    return template
    

@application.route("/cancel-subscription", methods=["GET", "POST"])
@application.route("/cancel-subscription/", methods=["GET", "POST"])
def cancel_subscription():
    template = None
    info = None
    logged_in = True
    subscribed = False

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])

      if not status["active"]:
        template = render_template("subscribe.html", profile=info, oidc=oidc, subscription=status)
      else:
        if not status["paid_user"] or status["group_user"]:
          unique_url = "%s%s"%(dashboard_url,username.replace("%40","@"))
          template = render_template("portal.html", profile=info, oidc=oidc, subscription=status, unique_url=unique_url)
        else:
          if request.method == "POST":
            billing_agreement = BillingAgreement.find(all_accounts[username]["subscription_id"])
            reason = request.form["reason"]
            if reason == "":
              reason = ":: No reason given ::"
            cancel_note = {"note": reason}
            try:
              billing_agreement.cancel(cancel_note)
              all_accounts[username]["subscribed"] = False
              for account in all_accounts:
                if all_accounts[account]["subscription_id"] == all_accounts[username]["subscription_id"]:
                  all_accounts[account]["subscribed"] = False
              upload_userinfo(all_accounts)
              template = redirect(url_for("cancel_success"), code=307)
            except:
              template = redirect(url_for("cancel_failed"), code=307)
          else:
            template = render_template("cancel-subscription.html", profile=info, oidc=oidc, subscription=status)
    else:
      template = redirect(url_for("login"))

    return template

@application.route("/privacypolicy")
@application.route("/privacypolicy/")
def privacypolicy():
    template = None
    info = None
    logged_in = True
    subscribed = False
    status = {"active": False}

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])

    template = render_template("privacypolicy.html", profile=info, oidc=oidc, subscription=status)
    return template

@application.route("/terms-of-use")
@application.route("/terms-of-use/")
def terms_of_use():
    template = None
    info = None
    logged_in = True
    subscribed = False
    status = {"active": False}

    try:
      info = oidc.user_getinfo(["sub", "name", "email", "locale"])
    except:
      logged_in = False

    if logged_in:
      all_accounts = get_userinfo()
      username = "/"+urllib.parse.quote(info["email"])
      status = get_subscription_status(all_accounts,
                                       username,
                                       all_accounts[username]["subscription_id"])

    template = render_template("terms-of-use.html", profile=info, oidc=oidc, subscription=status)
    return template
    

@application.route("/logout", methods=["POST"])
@application.route("/logout/", methods=["POST"])
def logout():
    oidc.logout()

    return redirect(url_for("portal"))


def base64_to_str(data):
    return str(base64.b64encode(json.dumps(data).encode('utf-8')), 'utf-8')
