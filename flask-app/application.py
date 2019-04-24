import sys
import plotly
from dash import Dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from plotly import tools
import plotly.graph_objs as go
plotly.tools.set_credentials_file(username='', api_key='')
import pandas as pd
#pd.options.mode.chained_assignment = None
import numpy as np
import datetime
import time
import pytz
import math
from math import sin, cos, radians
import re
import json
import random
random.seed(7)

from librul import rul

block_blob_service = rul.initializeBlobService()
testData = rul.loadTSDataFromBlobStorage(block_blob_service)

app = Dash(name='rul_demo')
app.title = 'IoTFuse 2019 | Predictive Maintenance'
app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})
app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/brPBPO.css"})

MAX_RUL = 300
alert_text = ["RUL > 30 cycles","RUL: 15 - 30 cycles","RUL < 15 cycles"]
alert_labels = ["Normal","Warn","Alarm"]
alert_messages = ["System healthy.<br>Maintenance not needed.",
                  "Warning.<br>Maintenance may be required soon.",
                  "Failure imminent.<br>Please schedule maintence."]
alert_colors = ['rgb(66, 244, 110)','rgb(255, 162, 56)','rgb(255, 73, 73)']
n_alerts = len(alert_labels)

unitList = [i for i in range(1,101)]

def rotate_point(point, angle, center_point=(0, 0)):
    angle_rad = radians(angle % 360)
    # Shift the point so that center_point becomes the origin
    new_point = (point[0] - center_point[0], point[1] - center_point[1])
    new_point = (new_point[0] * cos(angle_rad) - new_point[1] * sin(angle_rad),
                 new_point[0] * sin(angle_rad) + new_point[1] * cos(angle_rad))
    # Reverse the shifting we have done
    new_point = (new_point[0] + center_point[0], new_point[1] + center_point[1])
    return new_point

def draw_pointer(rotate_by,rotate_at):
    pointer_width = 0.008
    pointer_length = 0.2
    pointA = (rotate_at[0]-pointer_width/2,rotate_at[1])
    pointB = (rotate_at[0],rotate_at[1]+pointer_length)
    pointC = (rotate_at[0]+pointer_width/2,rotate_at[1])
    
    pointA,pointB,pointC = [rotate_point(pt,-rotate_by,rotate_at) for pt in [pointA,pointB,pointC]]
    s='M {} {} L {} {} L {} {} Z'.format(pointA[0],pointA[1],pointB[0],pointB[1],pointC[0],pointC[1])
    return s

def serve_layout():
    return html.Div(children=[
        html.Img(src="/static/iofuse-logo.png",style={'width':'15%'}),
        html.H2('Predictive Maintenance',style={'color':'grey'}),
        html.Div(children='''
        This analytics dashboard shows predictive maintenance alerts and tracks HVAC unit health.                                                                                            '''),
        html.Div(dcc.Dropdown(
            id='unitdropdown',
            options=[{'label': 'Turbofan unit # : '+str(unit),'value':unit} for unit in unitList],
            placeholder = "Select Unit...",
            value=1),style={'width': '30%', 'display': 'inline-block'}),
        html.Div(id='rul-perf-cache', style={'display': 'none'}),
        html.Div([
            dcc.Graph(
                id='sensor-graph',
                config={
                    'displayModeBar': False
                },
                className='six columns'),
            dcc.Graph(
                id='alert-graph',
                config={
                    'displayModeBar': False
                },
                className='three columns'),
            dcc.Graph(
                id='unit-metadata',
                config={
                    'displayModeBar': False
                },
                className='three columns')],className='row'),
        html.Div([
            dcc.Graph(
                id='metrics-graph',
                config={
                    'displayModeBar': False
                },
                className='six columns'),
            dcc.Graph(
                id='uptime-graph',
                config={
                    'displayModeBar': False
                },
                className='six columns')],className='row'),
        html.Br(),
    ],style={'text-align': 'center'})
    
app.layout = serve_layout()

@app.callback(Output('rul-perf-cache', 'children'), [Input('unitdropdown', 'value')])

def get_rul_data(unitNumber):
    unitNumber = int(unitNumber)
    if not unitNumber:
        raise PreventUpdate()
    trainingStats = rul.getTrainingStats(block_blob_service)#{'model_accuracy':0.95,'data_integrity':1.0}
    predictedAlert = rul.getPredictedAlert(testData,unitNumber)
    sensorData = rul.getLatestTS(testData,unitNumber,nCycles=10)
    
    uptimeStats = {'FIRST WARNING':0.290,'FIRST ALARM':0.493,'1 CYCLE BEFORE FAILURE':0.642}
    return json.dumps({'unitNumber':unitNumber,
                       'trainingStats':trainingStats,
                       'uptimeStats':uptimeStats,
                       'predictedAlert':predictedAlert,
                       'sensorData': sensorData.to_json(),
                       'cyclesSoFar': int(sensorData.index.max())})

@app.callback(Output('uptime-graph', 'figure'),[Input('rul-perf-cache', 'children')])

# calculate additional uptime gain for different maintenance schedules (compared to scheduled maintenance), i.e. % additional uptime by doing maintenance at:
# a) 1st warning,
# b) 1st alarm,
# c) 1 cycle before failure (perfect foresight)
def get_uptime_stats(cached_rul_data):
    cached_rul_data = json.loads(cached_rul_data)
    uptimeStats = cached_rul_data['uptimeStats']
    trace = go.Bar(x=list(uptimeStats.keys()),
                   y=[uptimeStats[k]*100.0 for k in uptimeStats.keys()],
                   marker=dict(color=[alert_colors[1],alert_colors[2],'rgb(204,204,204)']),
                   width=0.3,
                   hoverinfo="text",
                   text=['Gain %.2f%% additional uptime by doing maintenance upon %s'%(uptimeStats[k]*100.0,k.lower()) for k in uptimeStats.keys()],
                   name='% Uptime Gain')
    data = [trace]
    layout = go.Layout(
        title = "Additional Uptime Gain (Assuming Scheduled Maintenance Every 125 Cycles)",
        xaxis = dict(
            title='Maintenance Strategy'
        ),
        yaxis=dict(
            title='Uptime Gain (%)',
        ),
    )
    fig = go.Figure(data=data,layout=layout)
    return fig

@app.callback(Output('sensor-graph', 'figure'),[Input('rul-perf-cache', 'children')])

def get_sensor_graph(cached_rul_data):
    cached_rul_data = json.loads(cached_rul_data)
    unitNumber = cached_rul_data['unitNumber']
    sensorData = pd.read_json(cached_rul_data['sensorData'])
    
    trace0 = go.Bar(x=sensorData.index,
                    y=sensorData.StaticHPCOutletPres,
                    name='StaticHPCOutletPres',
                    marker=dict(
                        color='rgb(49,130,189)'
                    ),#mode='lines',
                    #line=dict(color='rgb(43, 156, 226)'),
                    yaxis='y',
                    width=0.3)
    trace1 = go.Bar(x=sensorData.index,y=[0],showlegend=False,hoverinfo='none')
    trace2 = go.Bar(x=sensorData.index,y=[0],yaxis='y2',showlegend=False,hoverinfo='none') 
    trace3 = go.Bar(x=sensorData.index,
                    y=sensorData.PhysCoreSpeed,
                    name='PhysCoreSpeed',
                    marker=dict(
                        color='rgb(204,204,204)'
                    ),
                    #mode='lines',
                    #line=dict(color='rgb(63, 95, 175)'),
                    yaxis='y2',
                    width=0.3)
    
    data = [trace0,trace1,trace2,trace3]

    layout = go.Layout(
        title = "Latest Sensor Data for Turbofan Unit #%s"%unitNumber,
        barmode='group',
        xaxis = dict(
            title='Cycle Count',
            domain=[0,0.95],
        ),
        yaxis=dict(
            title='Static HPC Outlet Pressure',
            range=[sensorData.StaticHPCOutletPres.min()-10,sensorData.StaticHPCOutletPres.max()+10]
        ),
        yaxis2=dict(
            title='Phys Core Speed',
            range=[sensorData.PhysCoreSpeed.min()-100,sensorData.PhysCoreSpeed.max()+100],
            overlaying='y',
            side='right',
            zeroline=False,
            showgrid=False,
        ))
        
    fig = go.Figure(data=data,layout=layout)
    return fig

@app.callback(Output('unit-metadata', 'figure'),[Input('rul-perf-cache', 'children')])

def get_unit_metadata(cached_rul_data):
    cached_rul_data = json.loads(cached_rul_data)
    install_date = '02/10/2017<br>'
    last_maintenance_date = '27/09/2018<br>'
    cycles_since_last_maintenance = cached_rul_data['cyclesSoFar']
    trace0 = go.Table(
        header=dict(values=['<b>Install Date</b>', '<b>Maintenance Date</b>'],
                    line = dict(color='rgb(49,130,189)'),
                    fill = dict(color='rgb(49,130,189)'),
                    font = dict(color = 'white'),
                    align = ['center']*2),
        cells=dict(values=[install_date,last_maintenance_date],
                   line = dict(color='rgb(49,130,189)'),
                   fill = dict(color='rgb(49,130,189)'),
                   font = dict(color = 'white'),
                   align = ['center'] * 2,
        ),
        domain=dict(y=[0,0.5])
    )
    trace1 = go.Table(
        header=dict(values=['<b>Cycles so far</b><br>'],
                    line = dict(color='rgb(49,130,189)'),
                    fill = dict(color='rgb(49,130,189)'),
                    font = dict(color = 'white'),
                    height = 40,
                    align = ['center']),
        cells=dict(values=[cycles_since_last_maintenance],
                   line = dict(color='rgb(49,130,189)'),
                   fill = dict(color='rgb(49,130,189)'),
                   font = dict(color = 'white', size = 46),
                   height = 70,
                   align = ['center'],
        ),
        domain=dict(y=[0.5,1]),
    )
    layout = dict(height=400)
    data = [trace0,trace1]
    fig = dict(data=data, layout=layout)
    return fig

@app.callback(Output('metrics-graph', 'figure'),[Input('rul-perf-cache', 'children')])

def get_data_stats_graph(cached_rul_data):
    cached_rul_data = json.loads(cached_rul_data)
    trainingStats = cached_rul_data['trainingStats']
    fig = {
        "data": [
            {
                "values": [trainingStats['model_accuracy'],1-trainingStats['model_accuracy']],
                "labels": [
                    "Accuracy",
                    " ",
                ],
                "textinfo":"none",
                "marker": {
                    'colors': [
                        'rgb(66, 134, 244)',
                        'rgb(255,255,255)',
                    ]
                },
                "name": "Data",
                "hoverinfo":"",
                "hole": .8,
                "type": "pie"
            }],
        "layout": {
            "title":"Training Data Stats",
            "showlegend":False,
            "hovermode":False,
            "annotations": [
                {
                    "font": {
                        "size": 20
                    },
                    "showarrow": False,
                    "text": "Model accuracy:<br>%d%%"%(trainingStats['model_accuracy']*100.0),
                },
            ]
        }
    }
    return {'data':fig}

@app.callback(Output('alert-graph', 'figure'),[Input('rul-perf-cache', 'children')])

def generate_alert_widget(cached_rul_data):
    cached_rul_data = json.loads(cached_rul_data)
    predicted_alert = cached_rul_data['predictedAlert']
    alert_message = alert_messages[predicted_alert]
    input_start, input_end, output_start, output_end = 0.0,2.0,-60.0,60.0 # output range depends on no. of labels!
    slope = 1.0 * (output_end - output_start) / (input_end - input_start)
    rotate_by = output_start + slope*(predicted_alert-input_start)
    rotate_at = (0.5,0.5)
    pointer_shape = draw_pointer(rotate_by=rotate_by, rotate_at=rotate_at)
    base_chart = {
        "values": [40]+[60/(n_alerts)]*(n_alerts),
        "labels": [" "]*(n_alerts+1),
        "domain": {"x": [0, 1]},
        "marker": {
            "colors": ['rgb(255, 255, 255)']*(n_alerts+2),
            "line": {
                "width": 1
            }
        },
        "name": "Gauge",
        "hole": .4,
        "type": "pie",
        "direction": "clockwise",
        "rotation": 108,
        "showlegend": False,
        "hoverinfo": "none",
        "textinfo": "label",
        "textposition": "outside"
    }
    
    meter_chart = {
        "values": [50]+[50/n_alerts]*n_alerts,
        "labels": ["<b>%s<b>"%alert_message]+alert_labels,
        'textfont': {
            'size': 12,
            'color':'rgb(0,0,0)'
        },
        "marker": {
            'colors': ['rgb(255,255,255)']+alert_colors,
        },
        "domain": {"x": [0, 1]},
        "name": "Gauge",
        "hole": .6,
        "type": "pie",
        "direction": "clockwise",
        "rotation": 90,
        "showlegend": False,
        "textinfo": "label",
        "textposition": "inside",
        "hoverinfo": "none"
    }
    
    layout = {
        'margin': {
            'l':10,
            'r':10,
        },
        'xaxis': {
            'showticklabels': False,
            'showgrid': False,
            'zeroline': False,
            'scaleanchor': 'y',
            'scaleratio': 0.5
        },
        'yaxis': {
            'scaleanchor': 'x',
            'scaleratio': 1.0,
            'showticklabels': False,
            'showgrid': False,
            'zeroline': False,
        },
        'shapes': [
            {
                'type': 'path',
                'path': pointer_shape,
                'fillcolor': 'rgb(0,0,0)',
                'line': {
                    'width': 0.5
                },
                'xref': 'paper',
                'yref': 'paper',
            }
        ],
        'annotations': [
            {
                'xref': 'paper',
                'yref': 'paper',
                'x': 0.5,
                'y': 0.45,
                'text': alert_text[predicted_alert],
                'font': {
                    'size': 16,
                    'color':'rgb(0,0,0)'
                },
                'showarrow': False
            }
        ]
    }
    
    # we don't want the boundary now
    base_chart['marker']['line']['width'] = 0

    fig = {"data": [base_chart, meter_chart],
           "layout": layout}
    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
