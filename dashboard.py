from datetime import datetime as dt
import re
import numpy as np
import plotly.graph_objs as go
import pandas as pd
from flask import request

import mortgage
import user_layout
import free_version

from config import *

from index import application
from index import app

@application.before_request
def before_request_func():
  agent = request.headers.get("User_Agent")
  mobile_string = "(?i)android|fennec|iemobile|iphone|opera (?:mini|mobi)|mobile"
  re_mobile = re.compile(mobile_string)
  is_mobile = False
  try:
    is_mobile = len(re_mobile.findall(agent)) > 0
  except TypeError:
    is_mobile = False

  line_width = 2
  plot_top = 30
  plot_font_size = 10
  static_plot = False
  show_legend = False

def month_diff(a, b):
  return 12 * (a.year - b.year) + (a.month - b.month)

free_layout = free_version.gen_free_version(False)

def fill_value(v, default):
  if v == None:
    v = default
  return v

def validate_inputs(p, 
                    r, 
                    extra, 
                    T, 
                    rp, 
                    rr, 
                    rT, 
                    start_month, 
                    start_year, 
                    refi_month, 
                    refi_year, 
                    lender_fees):

  error = False
  err_msg = ""

  p = fill_value(p, "300000")
  r = fill_value(r, "0.05")
  extra = fill_value(extra, "0")
  T = fill_value(T, "360")
  start_month = fill_value(start_month, "1")
  start_year = fill_value(start_year, "2010")
  rp = fill_value(rp, "200000")
  rr = fill_value(rr, "0.03")
  rT = fill_value(rT, "240")
  refi_month = fill_value(refi_month, "1")
  refi_year = fill_value(refi_year, "2020")
  lender_fees = fill_value(lender_fees, "3500")

  p = float(p)
  r = float(r)
  extra = float(extra)
  T = float(T)
  rp = float(rp)
  rr = float(rr)
  rT = float(rT)
  start_month = int(start_month)
  refi_month = int(refi_month)
  start_year = int(start_year)
  refi_year = int(refi_year)
  lender_fees = float(lender_fees)

  if p < 10000:
    err_msg = "Principal must be greater than 10000"
    p = 10000
  if rp < 10000:
    err_msg = "Refinanced principal must be greater than 10000"
    rp = 10000
  if extra < 0:
    extra = 0
  if start_year < 1990:
    err_msg = "Start year must be after 1990, reseting to default"
    #start_year = 2010
  if start_year > 2050:
    err_msg = "Start year must be before 2050, reseting to default"
    #start_year = 2010
  if refi_year < 1990:
    err_msg = "Refinance year must be after 1990, reseting to default"
    #refi_year = 2020
  if refi_year > 2050:
    err_msg = "Refinance year must be before 2050, reseting to default"
    #refi_year = 2020
  if refi_year < start_year:
    err_msg = "Origination year must be before refinance year"
    #refi_year = start_year + 1

  mort_end_year = start_year + int(T/12)

  if mort_end_year < refi_year:
    err_msg = "With current settings, mortgage is paid off before refinance"

  inputs = {"principal": p,
            "rate": r,
            "extra": extra,
            "term": T,
            "refi_principal": rp,
            "refi_rate": rr,
            "refi_term": rT,
            "start_month": start_month,
            "start_year": start_year,
            "refi_month": refi_month,
            "refi_year": refi_year,
            "lender_fees": lender_fees}

  return inputs

@app.callback(
  dash.dependencies.Output('payoff', 'figure'),
  [
    dash.dependencies.Input('url', 'pathname'),
    dash.dependencies.Input('principal', 'value'),
    dash.dependencies.Input('interest_rate', 'value'),
    dash.dependencies.Input('extra_payment', 'value'),
    dash.dependencies.Input('term', 'value'),
    dash.dependencies.Input('start_month', 'value'),
    dash.dependencies.Input('start_year', 'value'),
    dash.dependencies.Input('refi_amount', 'value'),
    dash.dependencies.Input('refi_interest_rate', 'value'),
    dash.dependencies.Input('refi_term', 'value'),
    dash.dependencies.Input('refi_start_month', 'value'),
    dash.dependencies.Input('refi_start_year', 'value'),
    dash.dependencies.Input('closing_costs', 'value')
  ])
def update_payoff(user, p, r, extra, T, start_month, start_year, rp, rr, rT, refi_month, refi_year, lender_fees):
  user = None
  #if not user == None and not user == "" and not user == "/":
  #  obj = s3.get_object(Bucket='refi-user-credentials',Key='accounts')
  #  serializedObject = obj['Body'].read()
  #  all_accounts = pickle.loads(serializedObject)
  #  user = user.replace("@","%40")
  agent = request.headers.get("User_Agent")
  mobile_string = "(?i)android|fennec|iemobile|iphone|opera (?:mini|mobi)|mobile"
  re_mobile = re.compile(mobile_string)
  is_mobile = False
  try:
    is_mobile = len(re_mobile.findall(agent)) > 0
  except TypeError:
    is_mobile = False

  line_width = 2
  plot_top = 30
  plot_font_size = 10
  static_plot = False
  show_legend = False

  scheme = "light"
  if not user == None and not user == "" and not user == "/":
    if user in all_accounts:
      if all_accounts[user]["subscribed"]:
        scheme = all_accounts[user]["scheme"]

  inputs = validate_inputs(p, 
                           r,
                           extra, 
                           T, 
                           rp, 
                           rr, 
                           rT, 
                           start_month, 
                           start_year, 
                           refi_month, 
                           refi_year, 
                           lender_fees)

  p = inputs["principal"]
  r = inputs["rate"]
  extra = inputs["extra"]
  T = inputs["term"]
  rp = inputs["refi_principal"]
  rr = inputs["refi_rate"]
  rT = inputs["refi_term"]
  start_month = inputs["start_month"]
  refi_month = inputs["refi_month"]
  start_year = inputs["start_year"]
  refi_year = inputs["refi_year"]
  lender_fees = inputs["lender_fees"]

  start_date = pd.Timestamp(start_year, start_month, 1)
  refi_date = pd.Timestamp(refi_year, refi_month, 1)
  if pd.isnull(start_date):
    start_date = base_start_date
  if pd.isnull(refi_date):
    refi_date = base_refi_date

  mortgages, base_payoff, refi_payoff, pi, rpi  = mortgage.get_mortgage_data(p, r, extra, T, start_date, rp, rr, rT, refi_date, lender_fees, True)

  payoff_x_1 = np.linspace(0, 1000, len(np.array(base_payoff)))
  payoff_y_1 = np.array(base_payoff) / 12
  payoff_x_2 = np.linspace(0, 1000, len(np.array(refi_payoff)))
  payoff_y_2 = np.array(refi_payoff) / 12

  
  payoff_fig = go.Figure()
  payoff_fig.add_trace(go.Scatter(x=payoff_x_1, y=payoff_y_1, name='Current',
                           mode='lines',
                           line=dict(color=colors[scheme]["lines"], width=line_width)))
  payoff_fig.add_trace(go.Scatter(x=payoff_x_2, y=payoff_y_2, name='Refinanced',
                           mode='lines',
                           line=dict(color=colors[scheme]["lines"], width=line_width,dash='dash')))
  payoff_fig.update_layout(title={'text': 'Time to Payoff Mortgage',
                                  'y': 0.95,
                                  'x': 0.5,
                                  'xanchor': 'center',
                                  'yanchor': 'top'},
                           xaxis_title='Extra paid towards principal ($)',
                           yaxis_title='Years',
                           margin=dict(
                             l=20,
                             r=10,
                             b=20,
                             t=plot_top,
                             pad=2
                           ),
                           font=dict(
                               family=font,
                               size=plot_font_size,
                               color=colors[scheme]["text"]
                           ),
                           showlegend = show_legend,
                           plot_bgcolor=colors[scheme]["plot_area"],
                           paper_bgcolor=colors[scheme]["plot_paper"],
                           hovermode = 'x unified')
  payoff_fig['layout']['xaxis1'].update(title='Extra paid towards principal ($)', range=[0.0, 1000.0], autorange=False, fixedrange=True)
  payoff_fig['layout']['yaxis1'].update(title='Years', range=[0, 35], autorange=False, fixedrange=True)

  return payoff_fig

@app.callback(
  dash.dependencies.Output('savings', 'figure'),
  [
    dash.dependencies.Input('url', 'pathname'),
    dash.dependencies.Input('principal', 'value'),
    dash.dependencies.Input('interest_rate', 'value'),
    dash.dependencies.Input('extra_payment', 'value'),
    dash.dependencies.Input('term', 'value'),
    dash.dependencies.Input('start_month', 'value'),
    dash.dependencies.Input('start_year', 'value'),
    dash.dependencies.Input('refi_amount', 'value'),
    dash.dependencies.Input('refi_interest_rate', 'value'),
    dash.dependencies.Input('refi_term', 'value'),
    dash.dependencies.Input('refi_start_month', 'value'),
    dash.dependencies.Input('refi_start_year', 'value'),
    dash.dependencies.Input('closing_costs', 'value')
  ])
def update_savings(user, p, r, extra, T, start_month, start_year, rp, rr, rT, refi_month, refi_year, lender_fees):
  user = None
  #if not user == None and not user == "" and not user == "/":
  #  obj = s3.get_object(Bucket='refi-user-credentials',Key='accounts')
  #  serializedObject = obj['Body'].read()
  #  all_accounts = pickle.loads(serializedObject)
  #  user = user.replace("@","%40")
  agent = request.headers.get("User_Agent")
  mobile_string = "(?i)android|fennec|iemobile|iphone|opera (?:mini|mobi)|mobile"
  re_mobile = re.compile(mobile_string)
  is_mobile = False
  try:
    is_mobile = len(re_mobile.findall(agent)) > 0
  except TypeError:
    is_mobile = False

  line_width = 2
  plot_top = 30
  plot_font_size = 10
  static_plot = False
  show_legend = False

  scheme = "light"
  if not user == None and not user == "" and not user == "/":
    if user in all_accounts:
      if all_accounts[user]["subscribed"]:
        scheme = all_accounts[user]["scheme"]

  inputs = validate_inputs(p, 
                           r,
                           extra, 
                           T, 
                           rp, 
                           rr, 
                           rT, 
                           start_month, 
                           start_year, 
                           refi_month, 
                           refi_year, 
                           lender_fees)

  p = inputs["principal"]
  r = inputs["rate"]
  extra = inputs["extra"]
  T = inputs["term"]
  rp = inputs["refi_principal"]
  rr = inputs["refi_rate"]
  rT = inputs["refi_term"]
  start_month = inputs["start_month"]
  refi_month = inputs["refi_month"]
  start_year = inputs["start_year"]
  refi_year = inputs["refi_year"]
  lender_fees = inputs["lender_fees"]

  start_date = pd.Timestamp(start_year, start_month, 1)
  refi_date = pd.Timestamp(refi_year, refi_month, 1)
  if pd.isnull(start_date):
    start_date = base_start_date
  if pd.isnull(refi_date):
    refi_date = base_refi_date

  y = int(refi_date.year) + int(rT / 12)
  m = int(refi_date.month)
  end_date = pd.Timestamp(y, m, 1)

  mortgages, base_payoff, refi_payoff, pi, rpi  = mortgage.get_mortgage_data(p, r, extra, T, start_date, rp, rr, rT, refi_date, lender_fees, False)

  #set1 = ((mortgages["m0_TIP"].to_numpy() - mortgages["r0_TIP"].to_numpy()) +
  #set1 += mortgages["me_TIP"].to_numpy()
  #set1 -= mortgages["re_TIP"].to_numpy()
  #set1 += mortgages["r0_TIP"].to_numpy()
  #set1 -= mortgages["me_TIP"].to_numpy()
  #set1 -= lender_fees
  set1 = np.zeros(len(mortgages["r0_Equity"].to_numpy()))
  set1 = ((mortgages["me_TIP"].to_numpy() - mortgages["re_TIP"].to_numpy()) +
          (mortgages["r0_Equity"].to_numpy() - mortgages["me_Equity"].to_numpy())
          - lender_fees)
  #set2 = ((mortgages["me_TIP"].to_numpy() - mortgages["re_TIP"].to_numpy()) +
  #        (mortgages["re_Equity"].to_numpy() - mortgages["me_Equity"].to_numpy())
  #        - lender_fees)
  savings_x_1 = mortgages["Date"]
  savings_y_1 = set1
  #savings_x_2 = mortgages["Date"]
  #savings_y_2 = set2
  savings_x_3 = np.array([start_date, end_date])
  savings_y_3 = np.array([0.0, 0.0])
  savings_fig = go.Figure()
  savings_fig.add_trace(go.Scatter(x=savings_x_1, y=savings_y_1, name='Savings',
                           line=dict(color=colors[scheme]["lines"], width=line_width, shape='spline', smoothing=1)))
  #savings_fig.add_trace(go.Scatter(x=savings_x_2, y=savings_y_2, name='%d extra/month'%(extra),
  #                         line=dict(color=colors[scheme]["lines"], width=2, shape='spline', smoothing=1,dash='dash')))
  savings_fig.add_trace(go.Scatter(x=savings_x_3, y=savings_y_3, name='Breakeven',
                           line=dict(color='rgb(125, 125, 125)', width=line_width+1)))
  savings_fig.update_layout(title={'text': 'Amount Saved by Refinancing',
                                   'y': 0.95,
                                   'x': 0.5,
                                   'xanchor': 'center',
                                   'yanchor': 'top'},
                    xaxis_title='Date',
                    yaxis_title='Savings ($)',
                    margin=dict(
                      l=20,
                      r=10,
                      b=20,
                      t=plot_top,
                      pad=2
                    ),
                    font=dict(
                        family=font,
                        size=plot_font_size,
                        color=colors[scheme]["text"]
                    ),
                    showlegend = show_legend,
                    plot_bgcolor=colors[scheme]["plot_area"],
                    paper_bgcolor=colors[scheme]["plot_paper"],
                    hovermode = 'x unified')
  #savings_fig['layout']['xaxis1'].update(title='Date', range=[refi_date, end_date], autorange=False)
  savings_fig['layout']['xaxis1'].update(title='Date', range=[refi_date, end_date], autorange=False, fixedrange=True)
  savings_fig['layout']['yaxis1'].update(title='Savings ($)', range=[np.nanmin(set1), np.nanmax(set1)], autorange=False, fixedrange=True)

  return savings_fig

@app.callback(
  dash.dependencies.Output('interest_min', 'figure'),
  [
    dash.dependencies.Input('url', 'pathname'),
    dash.dependencies.Input('principal', 'value'),
    dash.dependencies.Input('interest_rate', 'value'),
    dash.dependencies.Input('extra_payment', 'value'),
    dash.dependencies.Input('term', 'value'),
    dash.dependencies.Input('start_month', 'value'),
    dash.dependencies.Input('start_year', 'value'),
    dash.dependencies.Input('refi_amount', 'value'),
    dash.dependencies.Input('refi_interest_rate', 'value'),
    dash.dependencies.Input('refi_term', 'value'),
    dash.dependencies.Input('refi_start_month', 'value'),
    dash.dependencies.Input('refi_start_year', 'value'),
    dash.dependencies.Input('closing_costs', 'value')
  ])
def update_interest_min(user, p, r, extra, T, start_month, start_year, rp, rr, rT, refi_month, refi_year, lender_fees):
  user = None
  #if not user == None and not user == "" and not user == "/":
  #  obj = s3.get_object(Bucket='refi-user-credentials',Key='accounts')
  #  serializedObject = obj['Body'].read()
  #  all_accounts = pickle.loads(serializedObject)
  #  user = user.replace("@","%40")
  agent = request.headers.get("User_Agent")
  mobile_string = "(?i)android|fennec|iemobile|iphone|opera (?:mini|mobi)|mobile"
  re_mobile = re.compile(mobile_string)
  is_mobile = False
  try:
    is_mobile = len(re_mobile.findall(agent)) > 0
  except TypeError:
    is_mobile = False

  line_width = 2
  plot_top = 30
  plot_font_size = 10
  static_plot = False
  show_legend = False

  scheme = "light"
  if not user == None and not user == "" and not user == "/":
    if user in all_accounts:
      if all_accounts[user]["subscribed"]:
        scheme = all_accounts[user]["scheme"]

  inputs = validate_inputs(p, 
                           r,
                           extra, 
                           T, 
                           rp, 
                           rr, 
                           rT, 
                           start_month, 
                           start_year, 
                           refi_month, 
                           refi_year, 
                           lender_fees)

  p = inputs["principal"]
  r = inputs["rate"]
  extra = inputs["extra"]
  T = inputs["term"]
  rp = inputs["refi_principal"]
  rr = inputs["refi_rate"]
  rT = inputs["refi_term"]
  start_month = inputs["start_month"]
  refi_month = inputs["refi_month"]
  start_year = inputs["start_year"]
  refi_year = inputs["refi_year"]
  lender_fees = inputs["lender_fees"]

  start_date = pd.Timestamp(start_year, start_month, 1)
  refi_date = pd.Timestamp(refi_year, refi_month, 1)
  if pd.isnull(start_date):
    start_date = base_start_date
  if pd.isnull(refi_date):
    refi_date = base_refi_date

  mortgages, base_payoff, refi_payoff, pi, rpi  = mortgage.get_mortgage_data(p, r, extra, T, start_date, rp, rr, rT, refi_date, lender_fees, False)

  y = int(start_date.year) + int(T / 12)
  m = int(start_date.month)
  end_date = pd.Timestamp(y, m, 1)
  m_tip = mortgages["m0_TIP"].to_numpy()
  m_tip_f = np.nan_to_num(m_tip, copy=True, nan=np.nanmax(m_tip))
  r_dates = mortgages[mortgages["Date"] >= refi_date]["Date"]
  r_tip = mortgages[mortgages["Date"] >=
                    refi_date]["r0_TIP"].to_numpy()
  r_tip_f = r_tip.copy()
  if len(r_tip) > 0:
    r_tip_f = np.nan_to_num(r_tip, copy=True, nan=np.nanmax(r_tip))

  if r_dates.iloc[-1] > end_date:
    end_date = r_dates.iloc[-1]

  im_x_1 = mortgages["Date"]
  im_y_1 = m_tip_f
  im_x_2 = r_dates
  im_y_2 = r_tip_f
  
  im_fig = go.Figure()
  im_fig.add_trace(go.Scatter(x=im_x_1, y=im_y_1, name='Current',
                           line=dict(color=colors[scheme]["lines"], width=line_width, shape='spline', smoothing=1)))
  im_fig.add_trace(go.Scatter(x=im_x_2, y=im_y_2, name='Refinanced',
                           line=dict(color=colors[scheme]["lines"], width=line_width, shape='spline', smoothing=1,dash='dash')))
  im_fig.update_layout(title={'text': 'Interest Paid Making Minimum Payment',
                              'y': 0.95,
                              'x': 0.5,
                              'xanchor': 'center',
                              'yanchor': 'top'},
                    xaxis_title='Year',
                    yaxis_title='Interest paid ($)',
                    margin=dict(
                      l=20,
                      r=10,
                      b=20,
                      t=plot_top,
                      pad=2
                    ),
                    font=dict(
                        family=font,
                        size=plot_font_size,
                        color=colors[scheme]["text"]
                    ),
                    showlegend = show_legend,
                    plot_bgcolor=colors[scheme]["plot_area"],
                    paper_bgcolor=colors[scheme]["plot_paper"],
                    hovermode = 'x unified')
  imax = np.maximum(np.nanmax(m_tip)+20e3, np.nanmax(r_tip_f)+20e3)
  im_fig['layout']['xaxis1'].update(title='Year', range=[start_date, end_date], autorange=False)
  im_fig['layout']['yaxis1'].update(title='Interest paid', range=[0.0, imax], autorange=False)

  return im_fig

@app.callback(
  dash.dependencies.Output('interest_extra', 'figure'),
  [
    dash.dependencies.Input('url', 'pathname'),
    dash.dependencies.Input('principal', 'value'),
    dash.dependencies.Input('interest_rate', 'value'),
    dash.dependencies.Input('extra_payment', 'value'),
    dash.dependencies.Input('term', 'value'),
    dash.dependencies.Input('start_month', 'value'),
    dash.dependencies.Input('start_year', 'value'),
    dash.dependencies.Input('refi_amount', 'value'),
    dash.dependencies.Input('refi_interest_rate', 'value'),
    dash.dependencies.Input('refi_term', 'value'),
    dash.dependencies.Input('refi_start_month', 'value'),
    dash.dependencies.Input('refi_start_year', 'value'),
    dash.dependencies.Input('closing_costs', 'value')
  ])
def update_interest_extra(user, p, r, extra, T, start_month, start_year, rp, rr, rT, refi_month, refi_year, lender_fees):
  user = None
  #if not user == None and not user == "" and not user == "/":
  #  obj = s3.get_object(Bucket='refi-user-credentials',Key='accounts')
  #  serializedObject = obj['Body'].read()
  #  all_accounts = pickle.loads(serializedObject)
  #  user = user.replace("@","%40")
  agent = request.headers.get("User_Agent")
  mobile_string = "(?i)android|fennec|iemobile|iphone|opera (?:mini|mobi)|mobile"
  re_mobile = re.compile(mobile_string)
  is_mobile = False
  try:
    is_mobile = len(re_mobile.findall(agent)) > 0
  except TypeError:
    is_mobile = False

  line_width = 2
  plot_top = 30
  plot_font_size = 10
  static_plot = False
  show_legend = False

  scheme = "light"
  if not user == None and not user == "" and not user == "/":
    if user in all_accounts:
      if all_accounts[user]["subscribed"]:
        scheme = all_accounts[user]["scheme"]

  inputs = validate_inputs(p, 
                           r,
                           extra, 
                           T, 
                           rp, 
                           rr, 
                           rT, 
                           start_month, 
                           start_year, 
                           refi_month, 
                           refi_year, 
                           lender_fees)

  p = inputs["principal"]
  r = inputs["rate"]
  extra = inputs["extra"]
  T = inputs["term"]
  rp = inputs["refi_principal"]
  rr = inputs["refi_rate"]
  rT = inputs["refi_term"]
  start_month = inputs["start_month"]
  refi_month = inputs["refi_month"]
  start_year = inputs["start_year"]
  refi_year = inputs["refi_year"]
  lender_fees = inputs["lender_fees"]

  start_date = pd.Timestamp(start_year, start_month, 1)
  refi_date = pd.Timestamp(refi_year, refi_month, 1)
  if pd.isnull(start_date):
    start_date = base_start_date
  if pd.isnull(refi_date):
    refi_date = base_refi_date

  mortgages, base_payoff, refi_payoff, pi, rpi  = mortgage.get_mortgage_data(p, r, extra, T, start_date, rp, rr, rT, refi_date, lender_fees, False)

  y = int(start_date.year) + int(T / 12)
  m = int(start_date.month)
  end_date = pd.Timestamp(y, m, 1)

  m_tip = mortgages["m0_TIP"].to_numpy()
  m_tip_f = np.nan_to_num(m_tip, copy=True, nan=np.nanmax(m_tip))
  me_tip = mortgages["me_TIP"].to_numpy()
  me_tip_f = np.nan_to_num(me_tip, copy=True, nan=np.nanmax(me_tip))
  r_dates = mortgages[mortgages["Date"] >= refi_date]["Date"]
  r_tip = mortgages[mortgages["Date"] >=
                    refi_date]["re_TIP"].to_numpy()
  r_tip_f = np.nan_to_num(r_tip, copy=True, nan=np.nanmax(r_tip))
  if r_dates.iloc[-1] > end_date:
    end_date = r_dates.iloc[-1]
  
  im_e_x_1 = mortgages["Date"]
  im_e_y_1 = me_tip_f
  im_e_x_2 = r_dates
  im_e_y_2 = r_tip_f
  
  im_e_fig = go.Figure()
  im_e_fig.add_trace(go.Scatter(x=im_e_x_1, y=im_e_y_1, name='Current',
                           line=dict(color=colors[scheme]["lines"], width=line_width, shape='spline', smoothing=1)))
  im_e_fig.add_trace(go.Scatter(x=im_e_x_2, y=im_e_y_2, name='Refinanced',
                           line=dict(color=colors[scheme]["lines"], width=line_width, shape='spline', smoothing=1,dash='dash')))
  im_e_fig.update_layout(title={'text': 'Interest Paid Making Extra Principal Payment',
                                'y': 0.95,
                                'x': 0.5,
                                'xanchor': 'center',
                                'yanchor': 'top'},
                    xaxis_title='Year',
                    yaxis_title='Interest paid ($)',
                    margin=dict(
                      l=20,
                      r=10,
                      b=20,
                      t=plot_top,
                      pad=2
                    ),
                    font=dict(
                        family=font,
                        size=plot_font_size,
                        color=colors[scheme]["text"]
                    ),
                    showlegend = show_legend,
                    plot_bgcolor=colors[scheme]["plot_area"],
                    paper_bgcolor=colors[scheme]["plot_paper"],
                    hovermode = 'x unified')
  imax = np.maximum(np.nanmax(m_tip)+20e3, np.nanmax(r_tip_f)+20e3)
  im_e_fig['layout']['xaxis1'].update(title='Year', range=[start_date, end_date], autorange=False)
  im_e_fig['layout']['yaxis1'].update(title='Interest paid ($)', range=[0.0, imax], autorange=False)

  return im_e_fig

@app.callback(
  [
    dash.dependencies.Output('p_and_i_c', 'children'),
    dash.dependencies.Output('p_and_i_r', 'children')
  ],
  [
    dash.dependencies.Input('url', 'pathname'),
    dash.dependencies.Input('principal', 'value'),
    dash.dependencies.Input('interest_rate', 'value'),
    dash.dependencies.Input('extra_payment', 'value'),
    dash.dependencies.Input('term', 'value'),
    dash.dependencies.Input('start_month', 'value'),
    dash.dependencies.Input('start_year', 'value'),
    dash.dependencies.Input('refi_amount', 'value'),
    dash.dependencies.Input('refi_interest_rate', 'value'),
    dash.dependencies.Input('refi_term', 'value'),
    dash.dependencies.Input('refi_start_month', 'value'),
    dash.dependencies.Input('refi_start_year', 'value'),
    dash.dependencies.Input('closing_costs', 'value')
  ])
def update_p_and_i(user, p, r, extra, T, start_month, start_year, rp, rr, rT, refi_month, refi_year, lender_fees):
  user = user.replace("@","%40")

  inputs = validate_inputs(p, 
                           r,
                           extra, 
                           T, 
                           rp, 
                           rr, 
                           rT, 
                           start_month, 
                           start_year, 
                           refi_month, 
                           refi_year, 
                           lender_fees)

  p = inputs["principal"]
  r = inputs["rate"]
  extra = inputs["extra"]
  T = inputs["term"]
  rp = inputs["refi_principal"]
  rr = inputs["refi_rate"]
  rT = inputs["refi_term"]
  start_month = inputs["start_month"]
  refi_month = inputs["refi_month"]
  start_year = inputs["start_year"]
  refi_year = inputs["refi_year"]
  lender_fees = inputs["lender_fees"]

  start_date = pd.Timestamp(start_year, start_month, 1)
  refi_date = pd.Timestamp(refi_year, refi_month, 1)
  if pd.isnull(start_date):
    start_date = base_start_date
  if pd.isnull(refi_date):
    refi_date = base_refi_date

  mortgages, base_payoff, refi_payoff, pi, rpi  = mortgage.get_mortgage_data(p, r, extra, T, start_date, rp, rr, rT, refi_date, lender_fees, False)

  return "Principal and interest: $%7.2f"%(pi), "Principal and interest: $%7.2f"%(rpi)

@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname'),
               dash.dependencies.Input('url', 'search')])
def display_page(pathname, search):
  layout = free_layout

  #if not pathname == None and not pathname == "" and not pathname == "/":
  #  obj = s3.get_object(Bucket='refi-user-credentials',Key='accounts')
  #  serializedObject = obj['Body'].read()
  #  all_accounts = pickle.loads(serializedObject)
  #  #layout = free_version.gen_free_version()

  #  search = str(search)[1:]
  #  prefill = {}
  #  for s in search.split("&"):
  #    if len(s.split("=")) > 1:
  #      sname = s.split("=")[0]
  #      sval = s.split("=")[1]
  #      prefill[sname] = sval
  #  if not pathname == None:
  #    pathname = pathname.replace("@", "%40")
  #  if pathname in all_accounts and all_accounts[pathname]["subscribed"]:
  #    account = all_accounts[pathname]
  #    if account["subscribed"]:
  #      layout = user_layout.gen_layout(account, prefill)
  return layout

@app.callback(
  dash.dependencies.Output("payoff-modal-centered", "is_open"),
  [dash.dependencies.Input("payoff-open-centered", "n_clicks"), 
   dash.dependencies.Input("payoff-close-centered", "n_clicks")],
  [dash.dependencies.State("payoff-modal-centered", "is_open")],
)
def payoff_toggle_modal(n1, n2, is_open):
  if n1 or n2:
    return not is_open
  return is_open

@app.callback(
  dash.dependencies.Output("savings-modal-centered", "is_open"),
  [dash.dependencies.Input("savings-open-centered", "n_clicks"), 
   dash.dependencies.Input("savings-close-centered", "n_clicks")],
  [dash.dependencies.State("savings-modal-centered", "is_open")],
)
def savings_toggle_modal(n1, n2, is_open):
  if n1 or n2:
    return not is_open
  return is_open

@app.callback(
  dash.dependencies.Output("interest-min-modal-centered", "is_open"),
  [dash.dependencies.Input("interest-min-open-centered", "n_clicks"), 
   dash.dependencies.Input("interest-min-close-centered", "n_clicks")],
  [dash.dependencies.State("interest-min-modal-centered", "is_open")],
)
def int_min_toggle_modal(n1, n2, is_open):
  if n1 or n2:
    return not is_open
  return is_open

@app.callback(
  dash.dependencies.Output("interest-extra-modal-centered", "is_open"),
  [dash.dependencies.Input("interest-extra-open-centered", "n_clicks"), 
   dash.dependencies.Input("interest-extra-close-centered", "n_clicks")],
  [dash.dependencies.State("interest-extra-modal-centered", "is_open")],
)
def int_e_toggle_modal(n1, n2, is_open):
  if n1 or n2:
    return not is_open
  return is_open

@app.callback(
  dash.dependencies.Output("disclaimer-modal-centered", "is_open"),
  [dash.dependencies.Input("disclaimer-open-centered", "n_clicks"), 
   dash.dependencies.Input("disclaimer-close-centered", "n_clicks")],
  [dash.dependencies.State("disclaimer-modal-centered", "is_open")],
)
def disclaimer_toggle_modal(n1, n2, is_open):
  if n1 or n2:
    return not is_open
  return is_open
