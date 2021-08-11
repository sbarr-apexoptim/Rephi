import flask
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from flask_oidc import OpenIDConnect
from flask import Flask, flash, request, render_template, url_for, redirect, session, json

class CustomDash(dash.Dash):
    def interpolate_index(self, **kwargs):
        # Inspect the arguments by printing them
        #print(kwargs)
        return '''
        <!DOCTYPE html>
        <html lang="en">
            <head>
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','GTM-5QN9DHK');</script>
<!-- End Google Tag Manager -->
                <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1">
                <meta charset="UTF-8">
                <meta name="viewport" content=" width=device-width, initial-scale=1">
                <meta name="description" content="Use this interactive refinance calculator to get detailed analysis of your potential savings from refinancing your mortgage.">
                <meta name="keywords" content="refinance mortgage calculator">

                <meta property="og:title" content="Rephi - Refinance Calculator">
                <meta property="og:description" content="Use this interactive refinance calculator to get detailed analysis of your potential savings from refinancing your mortgage.">
                <meta property="og:image" content="https://refi-user-images.s3.amazonaws.com/rephi-text-bold-logo.png">
                <meta property="og:image:secure_url" content="https://refi-user-images.s3.amazonaws.com/rephi-text-bold-logo.png">
                <meta property="og:image:width" content="200.35">
                <meta property="og:image:height" content="95">
                <meta property="og:locale" content="en_US">
                <meta property="og:type" content="article">
                <meta property="og:site_name" content="Rephi">

                <title>Rephi - Refinance Calculator</title>
                <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
                <link rel="stylesheet" href="/assets/bootstrap.css" async>
                <link rel="stylesheet" href="/assets/style.css" async>
                <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto&display=swap" async>
                <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Open+Sans&display=swap" async>
            </head>
            <body>
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-5QN9DHK"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
              <div style="position: absolute; z-index: 10; height: 46px;">
                <div style="display: flex; z-index: 10; width: 100vw; height: 46px">
                  <div style="flex: 1; -webkit-flex; 1">
                    <h1 id="main-div" style="margin: 0; float: left; align: left; vertical-align: middle; textAlight: left; line-height: 46px; white-space: nowrap; font-weight: 400; color: #000000; text-shadow: 0px 0px 3px #FFFFFF;">Refinance Calculator</h1>
                  </div>
                  <div style="flex: 1; -webkit-flex; 1">
                    <a href="#">
                      <img src="/assets/rephi-logo-white-shadow.png" alt="Rephi logo" style="height: 46px; padding-right: 10px; float: right;"></img>
                    </a>
                  </div>
                </div>
              </div>
                {app_entry}
                {config}
                {scripts}
                {renderer}
            </body>
        </html>
        '''.format(
            app_entry=kwargs['app_entry'],
            config=kwargs['config'],
            scripts=kwargs['scripts'],
            renderer=kwargs['renderer'])

application = flask.Flask(__name__)
application.config.update({
    'SECRET_KEY': 'refi_app_key!',
    'OIDC_CLIENT_SECRETS': 'static/client_secrets.json',
    'OIDC_DEBUG': True,
    'OIDC_ID_TOKEN_COOKIE_SECURE': False,
    'OIDC_SCOPES': ["openid", "profile"],
    'OVERWRITE_REDIRECT_URI': 'https://rephi-dashboard.com/authorization-code/callback',
    'OIDC_CALLBACK_ROUTE': '/authorization-code/callback'
})

app = CustomDash(__name__,
                server=application,
                external_stylesheets=['assets/bootstrap.css',
                                      'assets/style.css',
                                      'https://use.fontawesome.com/releases/v5.7.2/css/all.css',
                                      'https://fonts.googleapis.com/css?family=Roboto'],
                external_scripts=['https://cdn.plot.ly/plotly-basic-1.54.3.min.js'],
                suppress_callback_exceptions=True)
app.css.config.serve_locally = True
app.scripts.config.serve_locally = True
application = app.server
app.title = 'Rephi - Refinance Calculator'

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

if __name__ == '__main__':
  application.run(host='0.0.0.0',port=8080)
