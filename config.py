from datetime import datetime as dt
import numpy as np
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd
import boto3
import botocore
import pickle

import mortgage

#s3 = boto3.client('s3')

#obj = s3.get_object(Bucket='refi-user-credentials',Key='accounts')
#serializedObject = obj['Body'].read()
#all_accounts = pickle.loads(serializedObject)

is_mobile = False
line_width = 2
plot_top = 30
plot_font_size = 10
static_plot = False

background_img = "assets/interlaced.png"
lender_fees = 3500
p = 300000
r = 0.05
T = 360
extra = 100
rp = 200000
rr = 0.03375
rT = 240
start_date = pd.Timestamp("2018, 7, 1")
refi_date = pd.Timestamp.today()
base_start_date = start_date
base_refi_date = refi_date

payoff_plot_description = html.Div([
                            dbc.Button("i", id="payoff-open-centered"),
                            dbc.Modal(
                              [
                                html.Div(style={'margin': 'auto'}),
                                dbc.ModalHeader("Payoff plot"),
                                dbc.ModalBody('The payoff plot compares the time to payoff both the current mortgage and the refinanced loan for a range of extra principal payments. This plot is useful to answer the question "How much extra principal payment do I need to make towards my mortgage to pay it off in the next 12, 15, 20 years?"'),
                                dbc.ModalFooter(
                                  dbc.Button(
                                    "Close", id="payoff-close-centered", className="ml-auto"
                                  )
                                ),
                                html.Div(style={'margin': 'auto'}),
                              ],
                              id="payoff-modal-centered",
                              centered=True,
                            ),
                          ],style={'position': 'absolute', 'top': '12px', 'left': '17px', 'height': '15px', 'z-index': '3'})

savings_plot_description = html.Div([
                            dbc.Button("i", id="savings-open-centered"),
                            dbc.Modal(
                              [
                                html.Div(style={'margin': 'auto'}),
                                dbc.ModalHeader("Savings plot"),
                                dbc.ModalBody('The most pressing question when refinancing is, "How long after I refinance will I breakeven on the closing costs?" Use this plot to help answer that question. The line represents your savings each year after you refinance assuming you pay the extra principal on only the current mortgage and the minimum payment on the refinanced loan. Initially, your savings are negative because you paid the lender fees to close. As a few months go by, you begin to save on interest compared to if you stay in your current mortgage, and as a result you are also accumulating equity at a faster rate. Your breakeven date is when the savings line crosses the horizontal line at zero. Do not be fooled by other refinance calculators that only compare the monthly payments to determine savings. Your true savings from refinancing can be calculated as the difference in accumulated interest paid between the refinaced loan and the current mortgage plus the difference in accumulated equity between the two loans minus the closing costs. This means your monthly payment could increase after refinancing, but if you are paying less in interest each month, you are saving money!'),
                                dbc.ModalFooter(
                                  dbc.Button(
                                    "Close", id="savings-close-centered", className="ml-auto"
                                  )
                                ),
                                html.Div(style={'margin': 'auto'}),
                              ],
                              id="savings-modal-centered",
                              centered=True,
                            ),
                          ],style={'position': 'absolute', 'top': '12px', 'left': '17px', 'height': '15px', 'z-index': '3'})

interest_min_plot_description = html.Div([
                            dbc.Button("i", id="interest-min-open-centered"),
                            dbc.Modal(
                              [
                                html.Div(style={'margin': 'auto'}),
                                dbc.ModalHeader("Interest paid making minimum payments"),
                                dbc.ModalBody('This plot shows the difference in the interest you will pay over the course of your current mortgage and your refinanced loan making the minimum payment.'),
                                dbc.ModalFooter(
                                  dbc.Button(
                                    "Close", id="interest-min-close-centered", className="ml-auto"
                                  )
                                ),
                                html.Div(style={'margin': 'auto'}),
                              ],
                              id="interest-min-modal-centered",
                              centered=True,
                            ),
                          ],style={'position': 'absolute', 'top': '12px', 'left': '17px', 'height': '15px', 'z-index': '3'})

interest_extra_plot_description = html.Div([
                            dbc.Button("i", id="interest-extra-open-centered"),
                            dbc.Modal(
                              [
                                html.Div(style={'margin': 'auto'}),
                                dbc.ModalHeader("Interest paid making extra principal payment"),
                                dbc.ModalBody('This plot shows the difference in the interest you will pay over the course of your current mortgage and your refinanced loan making an extra principal payment each month.'),
                                dbc.ModalFooter(
                                  dbc.Button(
                                    "Close", id="interest-extra-close-centered", className="ml-auto"
                                  )
                                ),
                                html.Div(style={'margin': 'auto'}),
                              ],
                              id="interest-extra-modal-centered",
                              centered=True,
                            ),
                          ],style={'position': 'absolute', 'top': '12px', 'left': '17px', 'height': '15px', 'z-index': '3'})

disclaimers = ""
disclaimers_modal = html.Div([
                               dbc.Button("Disclaimers", id="disclaimer-open-centered"),
                               dbc.Modal(
                                 [
                                   html.Div(style={'margin': 'auto'}),
                                   dbc.ModalHeader("Disclaimers"),
                                   dbc.ModalBody(disclaimers),
                                   dbc.ModalFooter(
                                     dbc.Button(
                                       "Close", id="disclaimer-close-centered", className="ml-auto"
                                     )
                                   ),
                                   html.Div(style={'margin': 'auto'}),
                                 ],
                                 id="disclaimer-modal-centered",
                                 centered=True,
                               ),
                             #],style={'position': 'absolute', 'top': '12px', 'left': '17px', 'height': '15px', 'z-index': '3'})
                             ], style={'padding-top': '10px'})

#font = "Arial"
#font = "Open Sans"
font = "Roboto"

sizes = {
  'page_heading': '36px',
  'heading': '20px',
  'legend': '18px',
  'name': '20px',
  'label': '12px',
  'plot': '12px'
}

colors = {
          "light": {
                     'background': '#e0e0e0',
                     'heading': '#e0e0e0',
                     'plot_area': '#e0e0e0',
                     'plot_paper': '#e0e0e0',
                     'lines': '#000000',
                     'border': '#1a1c22',
                     'text': '#000000',
                     'shadow': '#707070'
                   },
           "dark": {
                     'background': '#1a1c22',
                     'heading': '#30333c',
                     'plot_paper': '#30333c',
                     #'plot_area': '#1a1c22',
                     'plot_area': '#30333c',
                     'lines': '#339974',
                     'border': '#339974',
                     'text': '#ededed',
                     'shadow': '#000000'
                   },
           "apex": {
                     'background': '#1a1c22',
                     'heading': '#30333c',
                     'plot_paper': '#30333c',
                     #'plot_area': '#1a1c22',
                     'plot_area': '#30333c',
                     'lines': '#0080ff',
                     'border': '#192e3e',
                     'text': '#ededed',
                     'shadow': '#000000'
                   },
         }

rate_options = [{'label': '%g%%'%(100*n), 'value': n} for n in np.arange(start=0.01, stop=0.1001, step=0.00125)]

mortgages = pd.DataFrame()
base_payoff = []
refi_payoff = []
mortgages, base_payoff, refi_payoff, pi, rpi = mortgage.get_mortgage_data(p, r, extra, T, start_date, rp, rr, rT, refi_date, lender_fees, True)
default_mortgages, default_base_payoff, default_refi_payoff, default_pi, default_rpi = mortgage.get_mortgage_data(p, r, extra, T, start_date, rp, rr, rT, refi_date, lender_fees, True)

#payoff plot
payoff_x_1 = np.linspace(0, 1000, len(np.array(base_payoff)))
payoff_y_1 = np.array(base_payoff) / 12
payoff_x_2 = np.linspace(0, 1000, len(np.array(refi_payoff)))
payoff_y_2 = np.array(refi_payoff) / 12
payoff_fig = go.Figure()
payoff_fig.add_trace(go.Scatter(x=payoff_x_1, y=payoff_y_1, name='Current',
                         mode='lines',
                         line=dict(color=colors["dark"]["lines"], width=2, shape='spline', smoothing=1)))
payoff_fig.add_trace(go.Scatter(x=payoff_x_2, y=payoff_y_2, name='Refinanced',
                         mode='lines',
                         line=dict(color=colors["dark"]["lines"], width=2,dash='dash', shape='spline', smoothing=1)))
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
                           t=30,
                           pad=2
                         ),
                         font=dict(
                             family=font,
                             size=10,
                             color=colors["dark"]["text"]
                         ),
                         showlegend = False,
                         plot_bgcolor=colors["dark"]["plot_area"],
                         paper_bgcolor=colors["dark"]["plot_paper"],
                         hovermode = 'x unified')
payoff_fig['layout']['xaxis1'].update(title='Extra paid towards principal ($)', range=[0.0, 1000.0], autorange=False, fixedrange=True)
payoff_fig['layout']['yaxis1'].update(title='Years', range=[0, 35], autorange=False, fixedrange=True)

#savings plot
y = int(start_date.year) + int(T / 12)
m = int(start_date.month)
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
savings_fig.add_trace(go.Scatter(x=savings_x_1, y=savings_y_1, name='Minimum payment',
                         line=dict(color=colors["dark"]["lines"], width=2, shape='spline', smoothing=1)))
savings_fig.add_trace(go.Scatter(x=savings_x_3, y=savings_y_3,
                         line=dict(color='rgb(125, 125, 125)', width=3)))
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
                    t=30,
                    pad=2
                  ),
                  font=dict(
                      family=font,
                      size=10,
                      color=colors["dark"]["text"]
                  ),
                  showlegend = False,
                  plot_bgcolor=colors["dark"]["plot_area"],
                  paper_bgcolor=colors["dark"]["plot_paper"],
                  hovermode = 'x unified')
savings_fig['layout']['xaxis1'].update(title='Date', range=[start_date, end_date], autorange=False, fixedrange=True)
savings_fig['layout']['yaxis1'].update(title='Savings ($)', range=[np.nanmin(set1), np.nanmax(set1)], autorange=False, fixedrange=True)
