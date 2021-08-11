from datetime import datetime as dt
import numpy as np
import re
from flask import request
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd

from config import *

import mortgage

def gen_layout(account, prefill, check_mobile=True):
  obj = s3.get_object(Bucket='refi-user-credentials',Key='accounts')
  serializedObject = obj['Body'].read()
  all_accounts = pickle.loads(serializedObject)

  is_mobile = False
  is_ipad = False
  if check_mobile:
    agent = request.headers.get("User_Agent")
    if "iPad" in agent:
      is_ipad = True
    mobile_string = "(?i)android|fennec|iemobile|iphone|opera (?:mini|mobi)|mobile"
    re_mobile = re.compile(mobile_string)
    is_mobile = False
    try:
      is_mobile = len(re_mobile.findall(agent)) > 0
    except TypeError:
      is_mobile = False

  sizes = {
    'page_heading': '36px',
    'heading': '20px',
    'legend': '18px',
    'name': '20px',
    'label': '12px',
    'plot': '12px',
    'input_height': '30px',
    'company_info': '12px',
    'heading_div': 46,
    'social_button': '30px',
    'image': '95px',
    'tile': 110 # Tile height
  }
  line_width = 2
  plot_top = 30
  plot_font_size = 10
  static_plot = False
  show_legend = False
  #if is_mobile:
    #line_width = 4
    #plot_top = 50
    #plot_font_size = 20
    #static_plot = True
    #show_legend = True
    #sizes = {
    #  'page_heading': '72px',
    #  'heading': '24px',
    #  'legend': '30px',
    #  'name': '24px',
    #  'label': '24px',
    #  'plot': '16px',
    #  'input_height': '45px',
    #  'heading_div': 92,
    #  'social_button': '45px',
    #  'company_info': '18px',
    #  'image': '135px',
    #  'tile': 150 # Tile height
    #}
  
  ## Resolve default values
  default = {'principal': 250000,
             'interest_rate': 0.04625,
             'term': 360,
             'extra_principal': 100,
             'start_month': 7,
             'start_year': 2018,
             'refi_amount': 200000,
             'closing_costs': 5000,
             'refi_interest_rate': 0.03375,
             'refi_term': 240,
             'refi_month': pd.Timestamp.today().month,
             'refi_year': pd.Timestamp.today().year}

  for p in prefill:
    if p == "interest_rate" or p == "refi_interest_rate":
      default[p] = float(prefill[p])
    else:
      default[p] = int(prefill[p])

  scheme = account["scheme"]
  user_name = account["user_name"]
  email = account["email"]
  phone = account["phone"]
  nmls = "NMLS #%s"%(account["nmls"])
  title = account["title"]
  company_name = account["company"]
  address = account["address"]
  city_state = account["city_state"]
  org_nmls = account["org_nmls"]
  headshot_url = account["headshot_url"]
  company_logo_url = account["company_logo_url"]
  linkedin_url = account["linkedin_url"]
  facebook_url = account["facebook_url"]
  twitter_url = account["twitter_url"]
  include_fdic = account["include_fdic"]
  include_ehl = account["include_ehl"]

  org_logos = []
  org_logos.append(html.Div(style={'flex': '1', 'margin': 'auto'}))
  if include_ehl:
    org_logos.append(html.Img(src="https://refi-user-images.s3.amazonaws.com/EHL.png",
                        alt="equal housing lender logo",
                        style={
                          'flex': '1',
                          'width': '50px',
                          'padding-bottom': '10px',
                          'padding-right': '10px'
                        }
                      )
                    )
  if include_fdic:
    org_logos.append(html.Img(src="https://refi-user-images.s3.amazonaws.com/memberFDIC.png",
                        alt="FDIC logo",
                        style={
                          'flex': '1',
                          'width': '50px',
                          'padding-right': '10px'
                        }
                      )
                    )
  org_logos.append(html.Div(style={'flex': '1', 'margin': 'auto'}))

  disclaimers = ""
  if "disclaimers" in account:
    disclaimers = account["disclaimers"]
  disclaimers_modal = html.Div([
                                 dbc.Button("Disclaimers", id="disclaimer-open-centered"),
                                 dbc.Modal(
                                   [
                                     dbc.ModalHeader("Disclaimers"),
                                     dbc.ModalBody(disclaimers),
                                     dbc.ModalFooter(
                                       dbc.Button(
                                         "Close", id="disclaimer-close-centered", className="ml-auto"
                                       )
                                     ),
                                   ],
                                   id="disclaimer-modal-centered",
                                   centered=True,
                                 ),
                               #],style={'position': 'absolute', 'top': '12px', 'left': '17px', 'height': '15px', 'z-index': '3'})
                               ], style={'padding-top': '10px'})

  mortgages = pd.DataFrame()
  base_payoff = []
  refi_payoff = []
  lender_fees = default["closing_costs"]
  p = default["principal"]
  r = default["interest_rate"]
  T = default["term"]
  extra = default["extra_principal"]
  rp = default["refi_amount"]
  rr = default["refi_interest_rate"]
  rT = default["refi_term"]
  start_date = pd.Timestamp("%d, %d, 1"%(int(default["start_year"]),int(default["start_month"])))
  refi_date = pd.Timestamp("%d, %d, 1"%(int(default["refi_year"]),int(default["refi_month"])))
  base_start_date = start_date
  base_refi_date = refi_date
  mortgages, base_payoff, refi_payoff, pi, rpi  = mortgage.get_mortgage_data(p, r, extra, T, start_date, rp, rr, rT, refi_date, lender_fees, True)
  
  #payoff plot
  payoff_x_1 = np.linspace(0, 1000, len(np.array(base_payoff)))
  payoff_y_1 = np.array(base_payoff) / 12
  payoff_x_2 = np.linspace(0, 1000, len(np.array(refi_payoff)))
  payoff_y_2 = np.array(refi_payoff) / 12
  payoff_fig = go.Figure()
  payoff_fig.add_trace(go.Scatter(x=payoff_x_1, y=payoff_y_1, name='Current',
                           mode='lines',
                           line=dict(color=colors[scheme]["lines"], width=line_width, shape='spline', smoothing=1)))
  payoff_fig.add_trace(go.Scatter(x=payoff_x_2, y=payoff_y_2, name='Refinanced',
                           mode='lines',
                           line=dict(color=colors[scheme]["lines"], width=line_width,dash='dash', shape='spline', smoothing=1)))
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
  
  #savings plot
  y = int(refi_date.year) + int(rT / 12)
  m = int(refi_date.month)
  end_date = pd.Timestamp(y, m, 1)
  lender_fees = float(lender_fees)
  #set1 = ((mortgages["m0_TIP"].to_numpy() - mortgages["r0_TIP"].to_numpy()) +
  #        (mortgages["r0_Equity"].to_numpy() - mortgages["m0_Equity"].to_numpy())
  #        - lender_fees)
  set1 = np.zeros(len(mortgages["r0_Equity"].to_numpy()))
  set1 = ((mortgages["me_TIP"].to_numpy() - mortgages["re_TIP"].to_numpy()) +
          (mortgages["r0_Equity"].to_numpy() - mortgages["me_Equity"].to_numpy())
          - lender_fees)
  savings_x_1 = mortgages["Date"]
  savings_y_1 = set1
  savings_x_3 = np.array([pd.Timestamp(1950,1,1), pd.Timestamp(2200,1,1)])
  savings_y_3 = np.array([0.0, 0.0])
  savings_fig = go.Figure()
  savings_fig.add_trace(go.Scatter(x=savings_x_1, y=savings_y_1, name='Savings',
                           line=dict(color=colors[scheme]["lines"], width=line_width, shape='spline', smoothing=1)))
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
  savings_fig['layout']['xaxis1'].update(title='Date', range=[refi_date, end_date], autorange=False, fixedrange=True)
  savings_fig['layout']['yaxis1'].update(title='Savings ($)', range=[np.nanmin(set1), np.nanmax(set1)], autorange=False, fixedrange=True)
  
  #interest_min plot
  start_date = pd.Timestamp(start_date)
  refi_date = pd.Timestamp(refi_date)
  y = int(start_date.year) + int(T / 12)
  m = int(start_date.month)
  end_date = pd.Timestamp(y, m, 1)
  m_tip = mortgages["m0_TIP"].to_numpy()
  m_tip_f = np.nan_to_num(m_tip, copy=True, nan=np.nanmax(m_tip))
  r_dates = mortgages[mortgages["Date"] >= refi_date]["Date"]
  r_tip = mortgages[mortgages["Date"] >=
                    refi_date]["r0_TIP"].to_numpy()
  r_tip_f = np.nan_to_num(r_tip, copy=True, nan=np.nanmax(r_tip))
  
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
  imax = np.nanmax(m_tip)+20e3
  im_fig['layout']['xaxis1'].update(title='Year', range=[start_date, end_date], autorange=False, fixedrange=True)
  im_fig['layout']['yaxis1'].update(title='Interest paid ($)', range=[0.0, imax], autorange=False, fixedrange=True)
  
  #interest_extra plot
  m_tip = mortgages["m0_TIP"].to_numpy()
  m_tip_f = np.nan_to_num(m_tip, copy=True, nan=np.nanmax(m_tip))
  me_tip = mortgages["me_TIP"].to_numpy()
  me_tip_f = np.nan_to_num(me_tip, copy=True, nan=np.nanmax(me_tip))
  r_dates = mortgages[mortgages["Date"] >= refi_date]["Date"]
  r_tip = mortgages[mortgages["Date"] >=
                    refi_date]["re_TIP"].to_numpy()
  r_tip_f = np.nan_to_num(r_tip, copy=True, nan=np.nanmax(r_tip))
  
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
  imax = np.nanmax(m_tip)+20e3
  im_e_fig['layout']['xaxis1'].update(title='Year', range=[start_date, end_date], autorange=False, fixedrange=True)
  im_e_fig['layout']['yaxis1'].update(title='Interest paid ($)', range=[0.0, imax], autorange=False, fixedrange=True)

  plot_height = '35vh'
  #plot_height = '100%'
  #plot_height = '250px'
  #plot_height = '35%'
  #plot_height = 'calc( ( 100% - 200px ) / 2)'

  main_div_style = {
    'backgroundColor': colors[scheme]["background"],
    'width': '100%',
    'height': 'auto',
    '-webkit-overflow-scrolling': 'touch',
    'position': 'absolute',
    'top': '%dpx'%(sizes["heading_div"]+15),
    'bottom': '%dpx'%(sizes["tile"]),
    'overflow-x': 'hidden',
    'overflow-y': 'auto',
    'scrollbar-width': 'none',
  }
  if is_ipad:
    main_div_style["bottom"] = "%dpx"%(sizes["tile"]+75)
  
  heading_div_style = {
    'display': 'inline-block',
    #'position': 'relative',
    #'position': 'absolute',
    'z-index': '5',
    #'top': '0',
    'width': '100vw',
    'height': '%dpx'%(sizes["heading_div"]),
    #'margin-top': "0px",
    'background': colors[scheme]['heading'],
    '-webkit-box-shadow': '0px 0px 15px 5px %s'%(colors[scheme]["shadow"]),
    'box-shadow': '0px 0px 15px 5px %s'%(colors[scheme]["shadow"]),
  }

  footer_style = {
    'width': '100%', 
    'height': '%dpx'%(sizes["tile"]), 
    'background-color': colors[scheme]["background"], 
    'position': 'absolute', 
    'bottom': '0'
  }
  if is_ipad:
    footer_style["bottom"] = "75px"

  h1_style = {
    'margin': '0',
    'float': 'left',
    'align': 'left',
    'vertical-align': 'middle',
    'textAlign': 'left',
    'line-height': '%dpx'%(sizes["heading_div"]),
    'fontFamily': font,
    'font-size': sizes["page_heading"],
    'color': colors[scheme]['text'],
  }

  heading_div_style_l = {
    'margin': '1',
    'font-family': font,
    'font-size': sizes['label'],
    #'display': 'inline-block',
    'float': 'left',
    'vertical-align': 'middle',
    'align-self': 'center',
    'font-family': font,
    'line-height': '%dpx'%(sizes["heading_div"]),
    'padding-left': '10px',
    'height': '100%',
    'align': 'left',
    'color': colors[scheme]['text']
  }

  heading_div_style_r = {
    'margin': '1',
    'font-family': font,
    'font-size': sizes['label'],
    #'display': 'inline-block',
    'float': 'right',
    'vertical-align': 'middle',
    'align-self': 'center',
    'font-family': font,
    'line-height': '%dpx'%(sizes["heading_div"]),
    'padding-left': '10px',
    'height': '100%',
    'align': 'right',
    'color': colors[scheme]['text']
  }
  
  fs_style = {
    'display': 'inline-block',
    'font-family': font,
    'border': 'solid',
    'height': 'auto',
    'width': '100%',
    'padding-top': '5px',
    'padding-bottom': '5px',
    'border-color': colors[scheme]['border'],
    'background': colors[scheme]['heading'],
    '-webkit-box-shadow': '0px 0px 15px 5px %s'%(colors[scheme]["shadow"]), 
    'box-shadow': '0px 0px 15px 5px %s'%(colors[scheme]["shadow"]),
    'position': 'relative'
  }
  
  legend_style = {
    'font-family': font,
    'font-size': sizes['legend'],
    'width': 'auto',
    'line-height': 'inherit',
    'margin-left': '10px',
    'padding-top': '5px',
    'padding-left': '5px',
    'padding-right': '5px',
    'color': colors[scheme]['text'],
    'border-radius': '5px',
    'border': '1px solid black',
    'background': colors[scheme]['heading'],
  }
  
  label_style = {
    'flex': '1',
    'margin': 'auto',
    'justify-content': 'center',
    'align-items': 'center',
    'font-family': font,
    'font-size': sizes['label'],
    'color': colors[scheme]['text'],
    'padding-left': '5px',
    'width': '100%',
    'word-wrap': 'break-word',
    'vertical-align': 'middle',
  }
  
  input_style = {
    'flex': '1',
    'margin': 'auto',
    'justify-content': 'center',
    'align-items': 'center',
    'font-family': font,
    'font-size': sizes['label'],
    'vertical-align': 'middle',
    'line-height': '0',
    'width': '100%',
    'height': sizes["input_height"],
  }

  year_style = {
    'flex': '1',
    'margin': 'auto',
    'justify-content': 'center',
    'align-items': 'center',
    'font-family': font,
    'font-size': sizes['label'],
    'vertical-align': 'middle',
    'line-height': '0',
    'width': '100%',
    'height': sizes["input_height"],
  }
  
  dropdown_style = {
    'flex': '1',
    'margin': 'auto',
    'justify-content': 'center',
    'align-items': 'center',
    'font-family': font,
    'font-size': sizes["label"],
    'vertical-align': 'middle',
    'line-height': sizes["label"],
    #'line-height': '0',
    'height': sizes["input_height"],
    #'width': '10vw',
    'width': '100%',
    #'min-width': '80px',
    'vertical-align': 'middle',
    'padding': '0',
    #'display': 'block',
    #'background-color': colors[scheme]["background"],
    #'width': '150px'
  }
  
  plot_style = {
    'font-family': font,
    'font-size': sizes['plot'],
    'display': 'inline-block',
    #'height': '100%',
    'height': 'inherit',
    'min-height': '200px',
    #'width': '34vw',
    'width': '100%',
    '-webkit-box-shadow': '0px 0px 15px 5px %s'%(colors[scheme]["shadow"]), 
    'box-shadow': '0px 0px 15px 5px %s'%(colors[scheme]["shadow"]),
  }
  
  datepicker_style = {
    'vertical-align': 'middle',
    'line-height': '0',
    'width': '100%',
    #'width': '50%',
    #'min-width': '40px',
    'padding': '0',
    'z-index': 1,
  }
  
  bcard_name_style = {
    'margin': '0',
    'display': 'block',
    'vertical-align': 'middle',
    #'padding-top': '5px',
    'padding-bottom': '5px',
    'padding-left': '3px',
    'font-family': font,
    'font-size': sizes['name'],
    'line-height': sizes['label'],
    #'line-height': '10px',
    'color': colors[scheme]['text']
  }

  bcard_cname_style = {
    'margin': '0',
    'display': 'block',
    #'padding-top': '23px',
    'padding-bottom': '5px',
    'padding-left': '3px',
    'font-family': font,
    'font-size': sizes['name'],
    #'line-height': '10px',
    'line-height': sizes['label'],
    'color': colors[scheme]['text']
  }
  
  bcard_style = {
    'margin': '0',
    'font-family': font,
    'line-height': sizes['company_info'],
    'font-size': sizes['company_info'],
    'font-family': font,
    'display': 'block',
    #'line-height': '10px',
    'padding-top': '5px',
    'padding-left': '3px',
    'color': colors[scheme]['text']
  }

  disclaimer_button_style = {
    'margin': '0',
    'font-family': font,
    'font-size': sizes['label'],
    'font-family': font,
    'display': 'block',
    'line-height': '10px',
    'padding-top': '5px',
    'padding-left': '3px',
    'color': '#000000',
  }

  bcard_social_style = {
    'float': 'left',
    'margin': '0',
    'padding': '0',
    'padding-right': '5px',
  }

  bcard_div_style_r = {
    'margin': '1',
    'font-family': font,
    'font-size': sizes['label'],
    'float': 'right',
    'vertical-align': 'middle',
    'align-self': 'center',
    'font-family': font,
    'padding-left': '10px',
    'align': 'right',
    'color': colors[scheme]['text']
  }

  bcard_div_style_l = {
    'margin': '1',
    'font-family': font,
    'font-size': sizes['label'],
    'float': 'left',
    'vertical-align': 'middle',
    'align-self': 'center',
    'font-family': font,
    'padding-left': '10px',
    'align': 'left',
    'color': colors[scheme]['text']
  }
  
  bcard_col_style = {
    'display': 'flex',
    'display': '-webkit-flex',
    'flex-direction': 'row',
    '-webkit-flex-direction': 'row',
    'position': 'sticky',
    #'bottom': '0',
    #'left': '1vw',
    'margin': 'auto',
    #'margin-right': 'auto',
    #'margin-left': 'auto',
    '-webkit-box-shadow': '0px 0px 15px 5px %s'%(colors[scheme]["shadow"]), 
    'box-shadow': '0px 0px 15px 5px %s'%(colors[scheme]["shadow"]),
    #'height': '110px',
    'height': '%dpx'%(sizes["tile"]),
    'width': '98vw',
    'background': colors[scheme]['heading'],
    'border-radius': '5px',
    'z-index': '2',
    'overflow': 'auto',
    'overflow-x': 'auto',
  }

  social_buttons = []
  social_buttons.append(html.Div())
  if not linkedin_url == "" and not linkedin_url == "http://":
    social_buttons.append(html.A(html.Img(src="https://www.keesingtechnologies.com/wp-content/uploads/2018/07/Linkedin-Icon.png", alt="LinkedIn link", style={'height': sizes["social_button"], 'padding-top': '5px'}), target="_blank",href=linkedin_url, style=bcard_social_style))
  if not twitter_url == "" and not twitter_url == "http://":
    social_buttons.append(html.A(html.Img(src="https://cdn.pixabay.com/photo/2017/06/22/14/23/twitter-2430933_960_720.png", alt="Twitter link", style={'height': sizes["social_button"], 'padding-top': '5px'}), target="_blank",href=twitter_url, style=bcard_social_style))
  if not facebook_url == "" and not facebook_url == "http://":
    social_buttons.append(html.A(html.Img(src="https://cdn.pixabay.com/photo/2017/06/22/06/22/facebook-2429746_960_720.png", alt="Facebook link", style={'height': sizes["social_button"], 'padding-top': '5px'}), target="_blank",href=facebook_url, style=bcard_social_style))
  social_buttons.append(html.Div())
  
  layout = html.Div([
    html.Div([
      html.Div([
        #html.Div([
        #  html.H1("Rephi",
        #    id="main-div",
        #    style=h1_style
        #  ),
        #], style=heading_div_style_l),
        #html.Div([
        #  html.A([html.Img(src="assets/rephi-logo-white-shadow.png", alt="Rephi logo", style={'height': '%dpx'%(sizes["heading_div"]), 'padding-right': '10px'})], href="http://rephi-dashboard.com/portal")
        #], style=heading_div_style_r)
      ], style=heading_div_style),
    ], style={'background-color': colors[scheme]["background"], 'position': 'relative', 'height': '%dpx'%(sizes["heading_div"]+15)}),
  
    html.Div([
      html.Div([
        dbc.Row([
          dbc.Col([
            dbc.Row([
              dbc.Col([html.Fieldset([
                html.Legend("Current Mortgage", style=legend_style),
                dbc.Row([
                  dbc.Col([html.Label("Principal", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([dcc.Input(id='principal', type="number", value="%d"%(p), min='10000', style=input_style)], width=7, style={'ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'}),
                ], style={'flex-wrap': 'nowrap','padding-bottom': '4px', 'display': '-webkit-flex'}),
  
                dbc.Row([
                  dbc.Col([html.Label("Interest Rate", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([html.Div(dbc.Select(
                    id='interest_rate',
                    options=rate_options,
                    value=r, style=dropdown_style
                  ),style=dropdown_style)], width=7, style={'display': 'flex', 'ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'})
                ], style={'flex-wrap': 'nowrap', 'padding-bottom': '4px', 'display': '-webkit-flex'}),
  
                dbc.Row([
                  dbc.Col([html.Label("Term", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([html.Div(dbc.Select(
                    id='term',
                    options=[
                        {'label': '10 years', 'value': 120},
                        {'label': '11 years', 'value': 132},
                        {'label': '12 years', 'value': 144},
                        {'label': '13 years', 'value': 156},
                        {'label': '14 years', 'value': 168},
                        {'label': '15 years', 'value': 180},
                        {'label': '16 years', 'value': 192},
                        {'label': '17 years', 'value': 204},
                        {'label': '18 years', 'value': 216},
                        {'label': '19 years', 'value': 228},
                        {'label': '20 years', 'value': 240},
                        {'label': '21 years', 'value': 252},
                        {'label': '22 years', 'value': 264},
                        {'label': '23 years', 'value': 276},
                        {'label': '24 years', 'value': 288},
                        {'label': '25 years', 'value': 300},
                        {'label': '26 years', 'value': 312},
                        {'label': '27 years', 'value': 324},
                        {'label': '28 years', 'value': 336},
                        {'label': '29 years', 'value': 348},
                        {'label': '30 years', 'value': 360},
                    ],
                    value=T, style=dropdown_style
                  ), style=dropdown_style)], width=7, style={'display': 'flex', 'ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'})
                ], style={'flex-wrap': 'nowrap','padding-bottom': '4px', 'display': '-webkit-flex'}),
  
                dbc.Row([
                  dbc.Col([html.Label("Extra Principal", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([dcc.Input(id='extra_payment', type="number", value='%d'%(extra), min='0', style=input_style)], width=7, style={'ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'})
                ], style={'flex-wrap': 'nowrap','padding-bottom': '4px', 'display': '-webkit-flex'}),
  
                dbc.Row([
                  dbc.Col([html.Label("Start Date", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([
                    html.Div([html.Div(dbc.Select(
                      id='start_month',
                      #clearable=False,
                      #searchable=False,
                      #optionHeight=30,
                      options=[
                          {'label': 'January', 'value': 1},
                          {'label': 'February', 'value': 2},
                          {'label': 'March', 'value': 3},
                          {'label': 'April', 'value': 4},
                          {'label': 'May', 'value': 5},
                          {'label': 'June', 'value': 6},
                          {'label': 'July', 'value': 7},
                          {'label': 'August', 'value': 8},
                          {'label': 'September', 'value': 9},
                          {'label': 'October', 'value': 10},
                          {'label': 'November', 'value': 11},
                          {'label': 'December', 'value': 12},
                      ],
                      value=default["start_month"], style=dropdown_style),
                    style=dropdown_style)],style={'width': '60%'}),
                    html.Div(
                      dcc.Input(id="start_year", type="number", value='%d'%(int(default["start_year"])), min='1990', max='%d'%(int(pd.Timestamp.today().year)-1), style=year_style)
                    ,style={'padding-left': '1%', 'width': '40%'})
                  ], width=7, style={'display': 'flex', 'display': '-webkit-flex', 'flex-wrap': 'nowrap', 'width': '100%', 'ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'})
                ], style={'flex-wrap': 'nowrap', 'display': '-webkit-flex'}),
                dbc.Row([
                  html.Label(id="p_and_i_c", children="Principal and interest: $%7.2f"%(pi), style={
                                                                               'text-align': 'center', 
                                                                               'font-family': font, 
                                                                               'font-size': sizes['label'], 
                                                                               'color': colors[scheme]["text"],
                                                                               'padding-top': '5px', 
                                                                               'width': '100%',
                                                                              }
                  )
                ], style={'flex-wrap': 'nowrap', 'width': '100%'}),
              ], style=fs_style
              #)],width='auto'),
              )]),
            ], style={'flex-wrap': 'nowrap', 'padding-bottom': '5px'}),
            dbc.Row([
              dbc.Col([html.Fieldset([
                html.Legend("Refinanced Mortgage",
                  style=legend_style
                ),
  
                dbc.Row([
                  dbc.Col([html.Label("Principal", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([dcc.Input(id='refi_amount', type="number", value='%d'%(rp), min='10000', style=input_style)], width=7, style={'ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'}),
                ], style={'flex-wrap': 'nowrap','padding-bottom': '4px', 'display': '-webkit-flex'}),
  
                dbc.Row([
                  dbc.Col([html.Label("Closing Costs", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([dcc.Input(id='closing_costs', type="number", value='%d'%(lender_fees), style=input_style)], width=7, style={'ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'})
                ], style={'flex-wrap': 'nowrap','padding-bottom': '4px', 'display': '-webkit-flex'}),
  
                dbc.Row([
                  dbc.Col([html.Label("Interest Rate", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([html.Div(dbc.Select(
                    id='refi_interest_rate',
                      #clearable=False,
                      #searchable=False,
                    options=rate_options,
                    value=rr,
                    style=dropdown_style
                  ), style=dropdown_style)], width=7, style={'display': 'flex', 'ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'})
                ], style={'flex-wrap': 'nowrap','padding-bottom': '4px', 'display': '-webkit-flex'}),
  
                dbc.Row([
                  dbc.Col([html.Label("Term", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([html.Div(dbc.Select(
                    id='refi_term',
                      #clearable=False,
                      #searchable=False,
                    options=[
                        {'label': '10 years', 'value': 120},
                        {'label': '11 years', 'value': 132},
                        {'label': '12 years', 'value': 144},
                        {'label': '13 years', 'value': 156},
                        {'label': '14 years', 'value': 168},
                        {'label': '15 years', 'value': 180},
                        {'label': '16 years', 'value': 192},
                        {'label': '17 years', 'value': 204},
                        {'label': '18 years', 'value': 216},
                        {'label': '19 years', 'value': 228},
                        {'label': '20 years', 'value': 240},
                        {'label': '21 years', 'value': 252},
                        {'label': '22 years', 'value': 264},
                        {'label': '23 years', 'value': 276},
                        {'label': '24 years', 'value': 288},
                        {'label': '25 years', 'value': 300},
                        {'label': '26 years', 'value': 312},
                        {'label': '27 years', 'value': 324},
                        {'label': '28 years', 'value': 336},
                        {'label': '29 years', 'value': 348},
                        {'label': '30 years', 'value': 360},
                    ],
                    value=rT,
                    style=dropdown_style
                  ), style=dropdown_style)], width=7, style={'display': 'flex', 'ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'})
                ], style={'flex-wrap': 'nowrap','padding-bottom': '4px', 'display': '-webkit-flex'}),
  
                dbc.Row([
                  dbc.Col([html.Label("Start Date", style=label_style)], width = 5, style={'ms-flex': '0 0 38%', 'flex': '0 0 38%', 'max-width': '38%'}),
                  dbc.Col([
                    html.Div([html.Div(dbc.Select(
                      id='refi_start_month',
                      #clearable=False,
                      #searchable=False,
                      #optionHeight=30,
                      options=[
                          {'label': 'January', 'value': 1},
                          {'label': 'February', 'value': 2},
                          {'label': 'March', 'value': 3},
                          {'label': 'April', 'value': 4},
                          {'label': 'May', 'value': 5},
                          {'label': 'June', 'value': 6},
                          {'label': 'July', 'value': 7},
                          {'label': 'August', 'value': 8},
                          {'label': 'September', 'value': 9},
                          {'label': 'October', 'value': 10},
                          {'label': 'November', 'value': 11},
                          {'label': 'December', 'value': 12},
                      ],
                      value=default["refi_month"], style=dropdown_style),
                    style=dropdown_style)],style={'width': '60%'}),
                    html.Div(
                      dcc.Input(id="refi_start_year", type="number", value='%d'%(int(default["refi_year"])), min='%d'%(pd.Timestamp.today().year), max='3000', style=year_style)
                    ,style={'padding-left': '1px', 'width': '40%'})
                  ], width=7, style={'display': 'flex', 'display': '-webkit-flex', 'flex-wrap': 'nowrap', 'width': '100%','ms-flex': '0 0 62%', 'flex': '0 0 62%', 'max-width': '62%'})
                ], style={'flex-wrap': 'nowrap', 'display': '-webkit-flex'}),
                dbc.Row([
                  html.Label(id="p_and_i_r", children="Principal and interest: $%7.2f"%(rpi), style={
                                                                               'text-align': 'center', 
                                                                               'font-family': font, 
                                                                               'font-size': sizes['label'], 
                                                                               'color': colors[scheme]["text"],
                                                                               'padding-top': '5px', 
                                                                               'width': '100%',
                                                                              }
                  )
                ], style={'flex-wrap': 'nowrap', 'width': '100%'}),
              #], style=fs_style)],width='auto'),
              ], style=fs_style)]),
            ], style={'flex-wrap': 'nowrap'}),
          #], width='auto', style={'overflow-y': 'auto'}),
          #], lg=4),
          ], xl=3, style={'padding-bottom': '20px'}),
          dbc.Col([
            dbc.Row([
              dbc.Col([
                #dcc.Loading([
                  html.Div([
                    dcc.Graph(id = 'payoff', animate=True,
                              figure = payoff_fig,
                              config = {'staticPlot': static_plot, 'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d', 'zoomIn2d', 'zoomOut2d', 'pan2d', 'lasso2d', 'select2d']},
                    style=plot_style),
                    payoff_plot_description
                  #],style={'align': 'left', 'width': '100%', 'padding-top': '10px', 'height': 'calc((100vh - 165px)/2 - 10px)', 'min-height': '200px'})
                  ],style={'align': 'left', 'height': '100%', 'width': '100%', 'height': 'calc((100vh - %dpx)/2)'%(sizes["tile"]+sizes["heading_div"]+70), 'min-height': '200px'})
                  #],style={'align': 'left', 'height': '50vw', 'width': '100%', 'padding-top': '10px', 'min-height': '400px'})
                  #],style={'align': 'left', 'height': '100%', 'width': '100%', 'padding-top': '10px', 'min-height': '200px'})
                #], type='circle')
              ], xl=6, style={'height': '100%', 'padding': '10px'}),
              dbc.Col([
                #dcc.Loading([
                  html.Div([
                    dcc.Graph(id = 'savings', animate=True,
                              figure = savings_fig,
                              config = {'staticPlot': static_plot, 'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d', 'zoomIn2d', 'zoomOut2d', 'pan2d', 'lasso2d', 'select2d']},
                    style=plot_style),
                    savings_plot_description
                  #],style={'align': 'left', 'width': '100%', 'padding-top': '10px', 'height': 'calc((100vh - 165px)/2 - 10px)', 'min-height': '200px'})
                  ],style={'align': 'left', 'height': '100%', 'width': '100%', 'height': 'calc((100vh - %dpx)/2)'%(sizes["tile"]+sizes["heading_div"]+70), 'min-height': '200px'})
                  #],style={'align': 'left', 'height': '50vw', 'width': '100%', 'padding-top': '10px', 'min-height': '400px'})
                  #],style={'align': 'left', 'height': '100%', 'width': '100%', 'padding-top': '10px', 'min-height': '200px'})
                #], type='circle')
              ], xl=6, style={'height': '100%', 'padding': '10px'})
            #], justify="center", align="center", style={'padding-bottom': '10px'}),
            ], justify="center", align="center", style={}),
            dbc.Row([
              dbc.Col([
                #dcc.Loading([
                  html.Div([
                    dcc.Graph(id = 'interest_min', animate=True,
                              figure = im_fig,
                              config = {'staticPlot': static_plot, 'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d', 'zoomIn2d', 'zoomOut2d', 'pan2d', 'lasso2d', 'select2d']},
                    style=plot_style),
                    interest_min_plot_description
                  #],style={'align': 'left', 'width': '100%', 'padding-top': '10px', 'height': 'calc((100vh - 165px)/2 - 10px)', 'min-height': '200px'})
                  ],style={'align': 'left', 'height': '100%', 'width': '100%', 'height': 'calc((100vh - %dpx)/2)'%(sizes["tile"]+sizes["heading_div"]+70), 'min-height': '200px'})
                  #],style={'align': 'left', 'height': '50vw', 'width': '100%', 'padding-top': '10px', 'min-height': '400px'})
                  #],style={'align': 'left', 'height': '100%', 'width': '100%', 'padding-top': '10px', 'min-height': '200px'})
                #], type='circle')
              ], xl=6, style={'height': '100%', 'padding': '10px'}),
              dbc.Col([
                #dcc.Loading([
                  html.Div([
                    dcc.Graph(id = 'interest_extra', animate=True,
                              figure = im_e_fig,
                              config = {'staticPlot': static_plot, 'displaylogo': False, 'modeBarButtonsToRemove': ['zoom2d', 'zoomIn2d', 'zoomOut2d', 'pan2d', 'lasso2d', 'select2d']},
                    style=plot_style),
                    interest_extra_plot_description
                  #],style={'align': 'left', 'width': '100%', 'padding-top': '10px', 'height': 'calc((100vh - 165px)/2 - 10px)', 'min-height': '200px'})
                  ],style={'align': 'left', 'height': '100%', 'width': '100%', 'height': 'calc((100vh - %dpx)/2)'%(sizes["tile"]+sizes["heading_div"]+70), 'min-height': '200px'})
                  #],style={'align': 'left', 'height': '50vw', 'width': '100%', 'padding-top': '10px', 'min-height': '400px'})
                  #],style={'align': 'left', 'height': '100%', 'width': '100%', 'padding-top': '10px', 'min-height': '200px'})
                #], type='circle')
              ], xl=6, style={'height': '100%', 'padding': '10px'}),
            ], justify="center", align="center", style={'padding-bottom': '10px'}),
          #], width='auto')
          #], lg=8, style={'overflow-y': 'auto'})
          ], xl=9)
        #], style={'flex-wrap': 'nowrap', 'margin': '0', 'height': 'calc( 100% - 105px)'}),
        #], style={'margin': '0', 'height': 'calc( 100% - 115px)'}),
        ], style={'margin': '0', 'height': '100%'}),
        #], style={'flex-wrap': 'nowrap', 'margin': '0', 'height': 'calc( 100% - 95px)'}),
        #dbc.Row([
        #  dbc.Col([
      #], style={'margin': '0', 'height': 'calc(100vh - 57px)', 'width': '100vw'}),
      #], style={'overflow': 'scroll', 'margin': '0', 'height': 'calc(100vh - 110px)', 'width': '100vw'}),
      #], style={'overflow': 'auto', 'margin': '0', 'height': 'calc(100vh - 165px)', 'width': '100vw'}),
      #], style={'overflow': 'auto', 'margin': '0', 'height': 'calc(100vh - %dpx)'%(sizes["tile"]+sizes["heading_div"]+14), 'width': '100vw', '-webkit-overflow-scrolling': 'touch'}),
      ], style={'overflow': 'auto', 'margin': '0', 'height': 'auto', 'width': '100vw', '-webkit-overflow-scrolling': 'touch'}),
      #], style={'padding-top': '20px', 'flex-grow': '1', 'overflow': 'auto', 'margin': '0', 'height': 'auto', 'width': '100vw', '-webkit-overflow-scrolling': 'touch'}),
      #], style={'margin': '0', 'height': 'auto', 'width': '100vw'}),
    ], style=main_div_style),
    html.Div(
    #dbc.Col(
      html.Div([
        #html.Div(style={'flex': '1','margin':'auto'}),
        html.Div(
          html.Div([
            html.Div([
              html.Img(src=headshot_url, alt="user headshot", style={'height': sizes["image"], 'padding-left': '5px'}),
            ],style=bcard_div_style_l),
            html.Div([
              html.Div([
                #html.P(user_name, style=bcard_name_style),
                html.H1(user_name, style=bcard_name_style),
                html.I(title, style=bcard_style),
                html.H6(html.A(email, href='mailto:%s'%email), style=bcard_style),
                html.H6(phone, style=bcard_style),
                html.H6(nmls, style=bcard_style),
              ], style={'white-space': 'nowrap', 'vertical-align': 'middle', 'padding-top': '5px'})
            ], style=bcard_div_style_l),
            html.Div(
              social_buttons
            ,style={'margin': 'auto',
                    #'display': 'inline-grid',
                    'display': 'flex',
                    'display': '-webkit-flex',
                    'flex-direction': 'column',
                    '-webkit-flex-direction': 'column',
                    'padding-left': '10px',
                    #'vertical-align': 'middle',
                    'height': '100%',
                    #'align-self': 'center',
                    'line-height': sizes["social_button"],
                    'align': 'left'}),
          #], style={'display': 'flex', 'flex-direction': 'row', 'height': '110px'})
          ], style={'display': 'flex', 'display': '-webkit-flex', 'flex-direction': 'row', '-webkit-flex-direction': 'row', 'height': '%dpx'%(sizes["tile"])})
        ,style={'flex': '0 0 12em'}),
        html.Div(style={'flex': '1', 'margin': 'auto'}),
        html.Div(
          html.Div([
            html.Div(org_logos, style={"display": 'flex', 'display': '-webkit-flex', 'flex-direction': 'column', '-webkit-flex-direction': 'column'}),
            #html.Div([
            #  html.Img(src="https://refi-user-images.s3.amazonaws.com/EHL.png",
            #  style={
            #          'width': '50px',
            #          'padding-bottom': '10px',
            #          'padding-right': '10px'
            #        }),
            #  html.Img(src="https://refi-user-images.s3.amazonaws.com/memberFDIC.png",
            #  style={
            #          'width': '50px',
            #          'padding-right': '10px'
            #        })
            #], style=bcard_div_style_r),
            html.Div([
              html.Img(src=company_logo_url,
              alt="company logo",
              style={
                      'height': sizes["image"],
                      'padding-right': '10px'
                    })
            ], style=bcard_div_style_r),
            html.Div([
              html.Div([
                html.P(company_name, style=bcard_cname_style),
                html.H6(address, style=bcard_style),
                html.H6(city_state, style=bcard_style),
                html.H6("NMLS #%s"%org_nmls, style=bcard_style),
                disclaimers_modal,
              ], style={'white-space': 'nowrap', 'vertical-align': 'middle', 'padding-top': '5px'})
            ], style=bcard_div_style_r),
          #], style={'display': 'flex', 'flex-direction': 'row-reverse', 'height': '110px'})
          ], style={'display': 'flex', 'display': '-webkit-flex', 'flex-direction': 'row-reverse', '-webkit-flex-direction': 'row-reverse', 'height': '%dpx'%(sizes["tile"])})
        ,style={'flex': '0 0 12em'}),
        ], style=bcard_col_style)
    ,style=footer_style)
  #], style={'display': '-webkit-flex', '-webkit-flex-direction': 'column'})
  ],style={'background-color': colors[scheme]["background"]})
  #], style={'height': '100%'})
  
  return layout
