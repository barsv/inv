from dash import Dash, dcc, html, Input, Output, callback, clientside_callback, State, callback_context
import dash
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import forecast
import pandas as pd
from datetime import datetime

def create_chart_app(create_figure_func, on_period_change):

    app = Dash(__name__)
    app.layout = html.Div([
        html.Div([
            dcc.Graph(id='basic-interactions'),
            html.Div(id='hover-output', style={
                'position': 'absolute', 
                'top': '0', 
                'left': '10px'
        })
        ], style={ 'position': 'relative' }),
        # store to keep state of zoom/pan.
        dcc.Store(id='relayout-store'),
        # store to keep flag of a zoom being in progress.
        dcc.Store(id='scrolling-store', data={'scrolling': False}),
        # hidden input to pass events from client side javascript to the server.
        # see: https://gist.github.com/barsv/8691d92498b313748576a733d0ad1c3d
        dcc.Input(type='text', id='hidden-input', value='', style={'display': 'none'}),
        # buttons to change period of candles.
        html.Button('1m', id='one-min'),
        html.Button('5m', id='five-min'),
        html.Button('1h', id='one-hour'),
        html.Button('D', id='one-day'),
        # div for script that handles scroll events for the chart.
        html.Div(id='script-output')
    ])


    # This callback listens for events from client-side javascript. Currently client side js notifies server if a scrolling
    # is in progress (not completed) and the server stores the scrolling state flag to avoid server side triggered redraws 
    # of the chart while zoom is in progress to avoid chart blinking.
    @app.callback(
        Output('scrolling-store', 'data'),
        Input('hidden-input', 'value'), # listen for the hidden input value change.
        prevent_initial_call=True,
    )
    def update_output(value):
        print(f"Server received: {value}")
        return { 'scrolling': value == 'scrolling' }


    # this callback is triggered every time the chart is zoomed or panned.
    # note: relayoutData might have data only for 1 axis, for example, if the user zooms only on y axis. hence it's also
    # required to pass the relayout-store state and modify only changed fields in it.
    # once the store is updated the update will trigger the next callback that will recreate the chart.
    @callback(
        Output('relayout-store', 'data'),
        Input('basic-interactions', 'relayoutData'),
        State('relayout-store', 'data'))
    def on_relayoutData(relayoutData, relayout_store):
        print(f"relayoutData: {relayoutData}")
        if relayoutData is None:
            return dash.no_update
        if relayout_store is None:
            relayout_store = {}
        no_updates = True
        if 'dragmode' in relayoutData:
            relayout_store['dragmode'] = relayoutData['dragmode']
        if 'xaxis.range[0]' in relayoutData and ('xaxis.range[0]' not in relayout_store or relayout_store['xaxis.range[0]'] != relayoutData['xaxis.range[0]']):
            no_updates = False
            relayout_store['xaxis.range[0]'] = relayoutData['xaxis.range[0]']
        if 'xaxis.range[1]' in relayoutData and ('xaxis.range[1]' not in relayout_store or relayout_store['xaxis.range[1]'] != relayoutData['xaxis.range[1]']):
            no_updates = False
            relayout_store['xaxis.range[1]'] = relayoutData['xaxis.range[1]']
        if 'yaxis.range[0]' in relayoutData and ('yaxis.range[0]' not in relayout_store or relayout_store['yaxis.range[0]'] != relayoutData['yaxis.range[0]']):
            no_updates = False
            relayout_store['yaxis.range[0]'] = relayoutData['yaxis.range[0]']
        if 'yaxis.range[1]' in relayoutData and ('yaxis.range[1]' not in relayout_store or relayout_store['yaxis.range[1]'] != relayoutData['yaxis.range[1]']):
            no_updates = False
            relayout_store['yaxis.range[1]'] = relayoutData['yaxis.range[1]']
        if ('xaxis.autorange' in relayoutData or 'autosize' in relayoutData) and 'xaxis.range0' in relayout_store:
            no_updates = False
            relayout_store.pop('xaxis.range[0]', None)
            relayout_store.pop('xaxis.range[1]', None)
        if ('yaxis.autorange' in relayoutData or 'autosize' in relayoutData) and 'yaxis.range[0]' in relayout_store:
            no_updates = False
            relayout_store.pop('yaxis.range[0]', None)
            relayout_store.pop('yaxis.range[1]', None)
        if no_updates:
            print(f"no_updates")
            return dash.no_update
        print(f"relayout_store: {relayout_store}")
        return relayout_store


    @callback(
        Output('basic-interactions', 'figure'),
        Input('relayout-store', 'data'),
        Input('scrolling-store', 'data'),
        Input('one-min', 'n_clicks'),
        Input('five-min', 'n_clicks'),
        Input('one-hour', 'n_clicks'),
        Input('one-day', 'n_clicks'),
        # state is needed because this callback can be triggered not only by scrolling-store state changes but the state 
        # of scrolling is needed always for example if the user does pan.
        State('scrolling-store', 'data')) 
    def update_graph(relayout_store, scrolling_store, one_min, f_min, hour, day, scrolling_store_state):
        print('update_graph started')
        # if zooming is not stopped yet then don't recreate the figure. once the scrolling will be stopped the 
        # scrolling-state will get updated and this callback will be called once again.
        if scrolling_store_state['scrolling']:
            print('no update_graph because of scrolling')
            return dash.no_update
        global candles_df, selected_period
        # check if this callback was triggered by a button press. if it was then set the period of candles.
        ctx = callback_context
        button_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'no clicks yet'
        on_period_change(button_id)
        x0 = None
        x1 = None
        # slice dataframe so that there will be enough data to plot the chart and also have data on the left and right so 
        # that when the user starts to zoom/pan he will see data.
        if relayout_store and 'xaxis.range[0]' in relayout_store and 'xaxis.range[1]' in relayout_store:
            x0 = parse_date_by_length(relayout_store['xaxis.range[0]'])
            x1 = parse_date_by_length(relayout_store['xaxis.range[1]'])
        fig = create_figure_func(x0, x1)
        # apply current state of zoom/pan.
        if relayout_store:
            if 'xaxis.range[0]' in relayout_store and 'xaxis.range[1]' in relayout_store:
                # if there are several panes and multiple x axes then apply the same range for all of them.
                for axis in fig.layout:
                    if axis.startswith('xaxis'):
                        fig.layout[axis].update(range=[relayout_store['xaxis.range[0]'], relayout_store['xaxis.range[1]']])
            # keep zoom/pan position only for the top pane of the chart with candles.
            if 'yaxis.range[0]' in relayout_store and 'yaxis.range[1]' in relayout_store:
                fig.update_layout(yaxis=dict(range=[relayout_store['yaxis.range[0]'], relayout_store['yaxis.range[1]']]))
            # keep dragmode. otherwise the dragmode will be always getting reset to zoom after each chart redraw.
            if 'dragmode' in relayout_store:
                fig.update_layout(dragmode=relayout_store['dragmode'])
        return fig


    clientside_callback(
        """
    function(fig) {
        console.log('loading client side script');

        // Convert date string to UTC
        const convertToUTC = dateStr => dateStr.length === 10 ? `${dateStr}T00:00:00Z` : dateStr.split(' ').join('T') + 'Z';
        const convertToStr = date => date.toISOString().split('T').join(' ').replace('Z', '');

        const notifyServer = (msg) => {
            var input = document.getElementById('hidden-input');
            // setter is needed because under the hood React is used that tracks input state.
            var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            setter.call(input, msg); // sets value of the hidden input.
            input.dispatchEvent(new Event('input', { bubbles: true })); // bubbles is needed here.
        };

        const graphDiv = document.getElementById('basic-interactions').getElementsByClassName('js-plotly-plot')[0];
        const hoverOutput = document.getElementById('hover-output');

        let debounceTimeout;
        let isScrolling = false;

        if (!graphDiv) {
            return;
        }

        
        graphDiv.onwheel = function(event) {
            //debugger;
            console.log('onwheel started');

            event.preventDefault();

            // Set scrolling flag
            if (!isScrolling){
                console.log('notifying server: scrolling');
                isScrolling = true;
                notifyServer('scrolling');
            }

            // Debounce: wait for 200ms after the last scroll event to reset the flag
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                if (isScrolling) {
                    console.log('notifying server: no scrolling');
                    isScrolling = false;
                    notifyServer('not scrolling');
                }
            }, 200);

            const zoomLevel = 0.9; // Zoom out 5%
            const { xaxis, yaxis } = graphDiv.layout;

            //console.log('layout:');
            //console.log(graphDiv.layout);
            //console.log('xaxis.range: ' + xaxis.range);

            // Parse date strings to Date objects
            const xrange = xaxis.range.map(x => new Date(Date.parse(convertToUTC(x))));
            //console.log('xrange: ' + xrange);
            const yrange = yaxis.range;
            //console.log(yrange);

            // Calculate the zoom delta
            const dx = (xrange[1] - xrange[0]) * (1 - zoomLevel) / 2;
            const dy = (yrange[1] - yrange[0]) * (1 - zoomLevel) / 2;
            //console.log('dx: ' + dx);
            //console.log('dy: ' + dy);

            // Determine zoom direction
            const zoom = event.deltaY < 0 ? 1 : -1;

            let newX0date, newX1date, newX0, newX1;
            if (event.ctrlKey) {
                // Zoom around cursor position
                const cursorX = event.offsetX / graphDiv.clientWidth;
                const zoomDelta = (xrange[1] - xrange[0]) * (1 - zoomLevel);
                newX0date = new Date(xrange[0].getTime() + zoom * cursorX * zoomDelta);
                newX0 = convertToStr(newX0date);
                newX1date = new Date(xrange[1].getTime() - zoom * (1 - cursorX) * zoomDelta);
                newX1 = convertToStr(newX1date);
            } else if (event.shiftKey) {
                // Horizontal scroll
                const scrollDelta = -1 * (xrange[1] - xrange[0]) * 0.05 * zoom;
                newX0date = new Date(xrange[0].getTime() + scrollDelta);
                newX0 = convertToStr(newX0date);
                newX1date = new Date(xrange[1].getTime() + scrollDelta);
                newX1 = convertToStr(newX1date);
            } else {
                // Zoom with right edge fixed
                newX0date = new Date(xrange[0].getTime() + zoom * dx);
                newX0 = convertToStr(newX0date);
                newX1date = new Date(xrange[1].getTime());
                newX1 = xaxis.range[1];
            }

            // Compute new y range based on new x range
            const firstPaneRanges = graphDiv.data.filter(d => d.yaxis === 'y'); // not y2, y3, etc.
            const newYRanges = firstPaneRanges.map(trace => {
                const xValues = trace.x.map(x => new Date(Date.parse(convertToUTC(x))));
                let yMin, yMax;
                if (trace.y) {
                    const yValues = trace.y;
                    const withinRange = yValues.filter((y, i) => xValues[i] >= newX0date && xValues[i] <= newX1date);
                    yMax = Math.max(...withinRange);
                    yMin = Math.min(...withinRange);
                }
                else {
                    let yValues = trace.high;
                    let withinRange = yValues.filter((y, i) => xValues[i] >= newX0date && xValues[i] <= newX1date);
                    yMax = Math.max(...withinRange);
                    yValues = trace.low;
                    withinRange = yValues.filter((y, i) => xValues[i] >= newX0date && xValues[i] <= newX1date);
                    yMin = Math.min(...withinRange);
                }
                const yPadding = (yMax - yMin) * 0.05; // 5%
                yMin = yMin - yPadding;
                yMax = yMax + yPadding;
                return [yMin, yMax];
            });

            const newY0 = Math.min(...newYRanges.map(range => range[0]));
            const newY1 = Math.max(...newYRanges.map(range => range[1]));

            //console.log('new range y: ' + newY0 + ' ... ' + newY1);

            // Apply new ranges
            Plotly.relayout(graphDiv, {
                'xaxis.range[0]': newX0,
                'xaxis.range[1]': newX1,
                'yaxis.range[0]': newY0,
                'yaxis.range[1]': newY1,
            });
            console.log('onwheel completed');
        };

        const firstPaneSvg = graphDiv.getElementsByClassName('bglayer')[0].getElementsByClassName('bg')[0];

        const updateCursorLines = () => {
            // Get the plot's size and position
            const plotWidth = firstPaneSvg.width.baseVal.value;
            const plotHeight = firstPaneSvg.height.baseVal.value;

            // Calculate the corresponding data coordinates
            const xRange = graphDiv.layout.xaxis.range.map(x => new Date(convertToUTC(x)));
            const yRange = graphDiv.layout.yaxis.range;


            //const xData = new Date(xRange[0].getTime() + (window.mouseX / plotWidth) * (xRange[1] - xRange[0]));
            //const yData = yRange[0] + (1 - (window.mouseY / plotHeight)) * (yRange[1] - yRange[0]);
            const margin = graphDiv.layout.margin || { l: 0, r: 0, t: 0, b: 0 };

            const xData = new Date(xRange[0].getTime() + ((window.mouseX - margin.l) / plotWidth) * (xRange[1] - xRange[0]));
            const yData = yRange[0] + ((plotHeight - (window.mouseY - margin.t)) / plotHeight) * (yRange[1] - yRange[0]);

            // Prepare output data
            let output = `Time: ${convertToStr(xData)} `;

            graphDiv.data.forEach(trace => {
                if (trace.x) {
                    const xValues = trace.x.map(x => new Date(Date.parse(convertToUTC(x))));
                    const index = xValues.findIndex(xVal => xVal >= xData);
                    if (index !== -1) {
                        if (trace.y) {
                            output += `${trace.name || ''}: ${trace.y[index]}<br>`;
                        } else if (trace.high && trace.low && trace.open && trace.close) {
                            output += ` O${trace.open[index]} H${trace.high[index]}`
                                    + ` L${trace.low[index]} C${trace.close[index]} `
                                    //+ ` xData${xData} yData${yData}<br>`
                                    //+ ` mX${window.mouseX} mY${window.mouseY}<br>`
                                    //+ ` xRange[0]${xRange[0]} xRange[1]${xRange[1]}<br>`
                                    //+ ` w${plotWidth} h${plotHeight}<br>`
                                    ;
                        }
                    }
                }
            });

            // Update the hover-output div
            hoverOutput.innerHTML = output;
            
            // Add cursor lines
            window.cursorLines = [
                {
                    type: 'line',
                    x0: xData.toISOString(), y0: 0, x1: xData.toISOString(), y1: 1,
                    line: { color: 'black', width: 1, dash: 'dot' },
                    xref: 'x', yref: 'paper'
                },
                {
                    type: 'line',
                    x0: convertToStr(xRange[0]), y0: yData, x1: convertToStr(xRange[1]), y1: yData,
                    line: { color: 'black', width: 1, dash: 'dot' },
                    xref: 'x', yref: 'y'
                }
            ];
        };

        graphDiv.onmousemove = function(event) {
            console.log('onmousemove started');
            //debugger;
            
            if (isScrolling) {
                //return;
            }

            if (window.mouseX === event.offsetX && window.mouseY === event.offsetY) {
                return;
            }
            
            // Get the cursor position in pixels
            window.mouseX = event.offsetX;
            window.mouseY = event.offsetY;

            updateCursorLines();

            // note: Plotly.update is better than Plotly.relayout because update doesn't send relayout event to the server.
            Plotly.update(graphDiv, {}, {
                shapes: window.cursorLines
            }); 
            console.log('onmousemove completed');
        };

        // redraw cursor lines after each chart reloading.
        if (window.cursorLines) {
            Plotly.update(graphDiv, {}, {
                shapes: window.cursorLines
            }); 
        }
        
        console.log('script loading completed');
        return window.dash_clientside.no_update;
    }

        """,
        Output('script-output', 'children'),
        Input('basic-interactions', 'figure')
    )

    return app


# when server side code gets notified by client side js about current zoom/pan state for x axe it gets date time value
# in different formats. for example, if the range starts at the beginning of the day then the value doesn't have hours,
# minutes, seconds. this creates a proglem with parsing and i solve it using this hacky function.
def parse_date_by_length(date_string):
    # Check the length of the date string and determine the format
    date_length = len(date_string)
    if date_length < 11:
        # Date only (10 characters)
        date_format = '%Y-%m-%d'
    elif date_length < 17:
        # Without seconds (16 characters)
        date_format = '%Y-%m-%d %H:%M'
    elif date_length < 20:
        # Without milliseconds (19 characters)
        date_format = '%Y-%m-%d %H:%M:%S'
    elif date_length < 27:
        # With milliseconds (26 characters)
        date_format = '%Y-%m-%d %H:%M:%S.%f'
    else:
        raise ValueError(f"Date string '{date_string}' is not in a recognized format.")
    return datetime.strptime(date_string, date_format)