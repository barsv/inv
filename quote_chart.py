from dash import Dash, dcc, html, Input, Output, callback, clientside_callback, State, callback_context
import dash
from datetime import datetime

def create_chart_app(create_figure_func, on_period_change=None, period_buttons=None, debug=False):
    """
    Create a Dash chart application with given figure creation function and optional period change handler.

    Parameters:
    create_figure_func (function): Function to create the figure for the chart.
    on_period_change (function, optional): Function to handle period change events. Default is None.
    period_buttons (array, optional): Buttons to change candles period. Default is None.
    debug (bool, optional): Flag to enable or disable debug logging. Default is False.
    """
    app = Dash(__name__)
    layout_items = [
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
        # div for script that handles scroll events for the chart.
        html.Div(id='script-output')
    ]
    period_buttons_callback_inputs = []
    if on_period_change:
        if not period_buttons:
            period_buttons = [
                # buttons to change period of candles.
                html.Button('1m', id='1min'),
                html.Button('5m', id='5min'),
                html.Button('15m', id='15min'),
                html.Button('1h', id='1h'),
                html.Button('4h', id='4h'),
                html.Button('D', id='D'),
            ]
        layout_items += period_buttons
        period_buttons_callback_inputs = [Input(b.id, 'n_clicks') for b in period_buttons]
    app.layout = html.Div(layout_items)


    # This callback listens for events from client-side javascript. Currently client side js notifies server if a scrolling
    # is in progress (not completed) and the server stores the scrolling state flag to avoid server side triggered redraws 
    # of the chart while zoom is in progress to avoid chart blinking.
    @app.callback(
        Output('scrolling-store', 'data'),
        Input('hidden-input', 'value'), # listen for the hidden input value change.
        prevent_initial_call=True,
    )
    def update_output(value):
        """Update scrolling state based on client-side input."""
        if debug:
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
        """Handle relayout data for zooming and panning."""
        if debug:
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
            if debug:
                print(f"no_updates")
            return dash.no_update
        if debug:
            print(f"relayout_store: {relayout_store}")
        return relayout_store


    @callback(
        Output('basic-interactions', 'figure'),
        Input('relayout-store', 'data'),
        Input('scrolling-store', 'data'),
        # state is needed because this callback can be triggered not only by scrolling-store state changes but the state 
        # of scrolling is needed always for example if the user does pan.
        State('scrolling-store', 'data'),
        period_buttons_callback_inputs,
        ) 
    def update_graph(relayout_store, scrolling_store, scrolling_store_state, *args):
        """Update graph based on relayout store, scrolling store, and button clicks."""
        if debug:
            print('update_graph started')
        # if zooming is not stopped yet then don't recreate the figure. once the scrolling will be stopped the 
        # scrolling-state will get updated and this callback will be called once again.
        if scrolling_store_state['scrolling']:
            if debug:
                print('no update_graph because of scrolling')
            return dash.no_update
        global candles_df, selected_period
        # check if this callback was triggered by a button press. if it was then set the period of candles.
        if on_period_change:
            ctx = callback_context
            button_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else ''
            if button_id not in ['scrolling-store', 'relayout-store', 'scrolling-store-state']:
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
            if (DEBUG) {
                console.log('loading client side script');
            }

        // Convert date string to UTC
            const convertToUTC = dateStr => dateStr.length === 10 ? `${dateStr}T00:00:00Z` : dateStr.split(' ').join('T') + 'Z';
            const convertToStr = date => date.toISOString().split('T').join(' ').replace('Z', '');

            const notifyServer = (msg) => {
                var input = document.getElementById('hidden-input');
                // setter is needed because under the hood React is used that tracks input state.
                var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                setter.call(input, msg); // sets value of the hidden input.
                input.dispatchEvent(new Event('input', { bubbles: true }));
            };

            const graphDiv = document.getElementById('basic-interactions').getElementsByClassName('js-plotly-plot')[0];
            const hoverOutput = document.getElementById('hover-output');

            let debounceTimeout;
            let isScrolling = false;

            if (!graphDiv) {
                return;
            }

            graphDiv.onwheel = function(event) {
                if (DEBUG) {
                    console.log('onwheel started');
                }
                event.preventDefault();
                // Set scrolling flag
                if (!isScrolling){
                    if (DEBUG) {
                        console.log('notifying server: scrolling');
                    }
                    isScrolling = true;
                    notifyServer('scrolling');
                }

                // Debounce: wait for 200ms after the last scroll event to reset the flag
                clearTimeout(debounceTimeout);
                debounceTimeout = setTimeout(() => {
                    if (isScrolling) {
                        if (DEBUG) {
                            console.log('notifying server: no scrolling');
                        }
                        isScrolling = false;
                        notifyServer('not scrolling');
                    }
                }, 200);

                const zoomLevel = 0.9; // Zoom out 10%
                const { xaxis, yaxis } = graphDiv.layout;

                // Parse date strings to Date objects
                const xrange = xaxis.range.map(x => new Date(Date.parse(convertToUTC(x))));
                const yrange = yaxis.range;

                // Calculate the zoom delta
                const dx = (xrange[1] - xrange[0]) * (1 - zoomLevel) / 2;
                const dy = (yrange[1] - yrange[0]) * (1 - zoomLevel) / 2;

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
                const firstPaneRanges = graphDiv.data.filter(d => d.yaxis === 'y');
                const newYRanges = firstPaneRanges.map(trace => {
                    const xValues = getXValues(trace);
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

                // Apply new ranges
                Plotly.relayout(graphDiv, {
                    'xaxis.range[0]': newX0,
                    'xaxis.range[1]': newX1,
                    'yaxis.range[0]': newY0,
                    'yaxis.range[1]': newY1,
                });
                if (DEBUG) {
                    console.log('onwheel completed');
                }
            };

            const bglayer = graphDiv.getElementsByClassName('bglayer')[0];
            const firstPaneSvg = bglayer.getElementsByClassName('bg')[0];
                
            const xValuesMap = {};
            const getXValues = (trace) => {
                const key = `${trace.name}-${trace.yaxis}`;
                const existingValue = xValuesMap[key];
                if (existingValue) {
                    return existingValue;
                }
                const xValues = trace.x.map(x => new Date(Date.parse(convertToUTC(x))));
                xValuesMap[key] = xValues;
                return xValues;
            };

            function findNearestIndex(xValues, xData) {
                let left = 0;
                let right = xValues.length - 1;

                // Check corner cases.
                if (xData <= xValues[left]) return left;
                if (xData >= xValues[right]) return right;

                while (left <= right) {
                    let mid = Math.floor((left + right) / 2);

                    if (xValues[mid] === xData) {
                        return mid; // Exact match.
                    } else if (xValues[mid] < xData) {
                        left = mid + 1;
                    } else {
                        right = mid - 1;
                    }
                }

                // After the loop, left will point to the first element that is greater than xData.
                // Compare the distance between xData and neighbour points.
                if (left === 0) return 0;
                if (left === xValues.length) return xValues.length - 1;

                const leftDiff = Math.abs(xValues[left - 1] - xData);
                const rightDiff = Math.abs(xValues[left] - xData);

                return leftDiff <= rightDiff ? left - 1 : left;
            }

            const updateCursorLines = () => {
                // Get the plot's size and position.
                const plotWidth = firstPaneSvg.width.baseVal.value;
                const plotHeight = firstPaneSvg.height.baseVal.value;

                // Calculate the corresponding data coordinates
                const xRange = graphDiv.layout.xaxis.range.map(x => new Date(convertToUTC(x)));
                const yRange = graphDiv.layout.yaxis.range;

                const graphRect = graphDiv.getBoundingClientRect();
                const bgRect = bglayer.getBoundingClientRect();
                const left = bgRect.x - graphRect.x;
                const top = bgRect.y - graphRect.y;
                const relativeX = window.mouseX - left;
                const relativeY = window.mouseY - top;

                const xData = new Date(xRange[0].getTime() + (relativeX / plotWidth) * (xRange[1] - xRange[0]));
                const yData = yRange[0] + ((plotHeight - relativeY) / plotHeight) * (yRange[1] - yRange[0]);

                // find OHLC trace
                const ohlc = graphDiv.data.find(trace => trace.high);
                // find Volume trace
                const volume = graphDiv.data.find(trace => trace.name === 'Volume');

                let xValues = getXValues(ohlc);
                let index = findNearestIndex(xValues, xData);
                if (index === -1) {
                    return;
                }
                let output = '<div>'
                    + `${convertToStr(xData)}`
                    + ` O${ohlc.open[index]} H${ohlc.high[index]}`
                    + ` L${ohlc.low[index]} C${ohlc.close[index]}`
                    + ` V${volume.y[index]}`;
                if (DEBUG) {
                    output += `<br>xData${xData.toISOString()} yData${yData}<br>`
                        + `mX${window.mouseX} mY${window.mouseY}<br>`
                        + `relativeX${relativeX} relativeY${relativeY} <br>`
                        + `xRange[0]${xRange[0].toISOString()} xRange[1]${xRange[1].toISOString()}<br>`
                        + `w${plotWidth} h${plotHeight}<br>`;
                }
                output += '</div>';

                // Add info from other non ohlc/volume traces.
                graphDiv.data.forEach(trace => {
                    if (!(trace.high && trace.low && trace.open && trace.close) && trace.name !== 'Volume') {
                        xValues = getXValues(ohlc);
                        index = findNearestIndex(xValues, xData);
                        if (index === -1) {
                            return;
                        }
                        output += `<div>${trace.name || ''}: ${trace.y[index]}</div>`;
                    }
                });

                // Update the hover-output div
                const style = `
                    width: 0;
                    font-family: 'Open Sans', verdana, arial, sans-serif; 
                    font-size: 12px; 
                    fill: rgb(42, 63, 95);
                    fill-opacity: 1;
                    font-weight: normal;
                    font-style: normal; 
                    font-variant: normal;
                    white-space: pre;
                `;
                hoverOutput.innerHTML = `<div style="${style}">${output}</div>`;

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
                if (DEBUG) {
                    console.log('onmousemove started');
                }
                
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
                if (DEBUG) {
                    console.log('onmousemove completed');
                }
            };

            if (window.cursorLines) {
                Plotly.update(graphDiv, {}, {
                    shapes: window.cursorLines
                });
            }
            
            if (DEBUG) {
                console.log('script loading completed');
            }
            return window.dash_clientside.no_update;
        }
        """.replace("DEBUG", str(debug).lower()),
        Output('script-output', 'children'),
        Input('basic-interactions', 'figure')
    )

    return app


# when server side code gets notified by client side js about current zoom/pan state for x axe it gets date time value
# in different formats. for example, if the range starts at the beginning of the day then the value doesn't have hours,
# minutes, seconds. this creates a proglem with parsing and i solve it using this hacky function.
def parse_date_by_length(date_string):
    """
    Parse date string into a datetime object, handling various date formats.

    Parameters:
    date_string (str): Date string to be parsed.

    Returns:
    datetime: Parsed datetime object.
    """
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
