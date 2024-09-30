import time
import csv
from arduino_iot_cloud import ArduinoCloudClient
import plotly.graph_objs as go
import dash
from dash import dcc, html
import threading
import os

# Arduino Cloud Configuration
DEVICE_ID = "cded3de5-b451-4fc7-a122-8462f219cee8"
SECRET_KEY = "G@4wxGQ4MKXlUKSQPzx!WjNvD"

# File name for storing all captured data
ALL_DATA_CSV_FILE = "all_accelerometer_data.csv"
PLOT_DATA_CSV_FILE = "plot_accelerometer_data.csv"

# Store values temporarily
values = {"py_x": None, "py_y": None, "py_z": None}
data_storage = []  # Continuous data buffer
plot_data = []     # Data used for plotting

# Buffer size for samples to visualize
BUFFER_SIZE = 15

# Open CSV file for writing all captured data
all_data_file = open(ALL_DATA_CSV_FILE, 'a', newline='')
all_data_csv_writer = csv.writer(all_data_file)

# Initialize the plot CSV file
plot_data_file = open(PLOT_DATA_CSV_FILE, 'w', newline='')
plot_data_csv_writer = csv.writer(plot_data_file)
plot_data_csv_writer.writerow(['Timestamp', 'py_x', 'py_y', 'py_z'])

# Callback function for accelerometer values
def on_value_changed(client, variable_name, value):
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        values[variable_name] = value
        if all(v is not None for v in values.values()):
            # Save the data to the continuous buffer
            data_storage.append([timestamp, values["py_x"], values["py_y"], values["py_z"]])
            all_data_csv_writer.writerow([timestamp, values["py_x"], values["py_y"], values["py_z"]])
            all_data_file.flush()  # Ensure data is written to the file
            print(f"Data recorded: py_x={values['py_x']}, py_y={values['py_y']}, py_z={values['py_z']} at {timestamp}")
            
            # Reset values after writing
            values["py_x"] = values["py_y"] = values["py_z"] = None

            # Check if buffer has 10 samples
            if len(data_storage) >= BUFFER_SIZE:
                # Move BUFFER_SIZE samples from data_storage to plot_data
                plot_data.clear()
                plot_data.extend(data_storage[:BUFFER_SIZE])

                # Save the 10-sample data to another CSV file
                save_to_csv(plot_data, PLOT_DATA_CSV_FILE)

                # Plot the 10-sample data in the Plotly Dash app
                launch_dash_app(plot_data)

                # Remove the samples from the continuous buffer
                del data_storage[:BUFFER_SIZE]
    except Exception as e:
        print(f"Error in on_value_changed: {e}")

# Function to save the last 10 captured data to CSV for plotting
def save_to_csv(data, file_name):
    with open(file_name, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'py_x', 'py_y', 'py_z'])
        writer.writerows(data)
    print(f"Plot data saved to {file_name}")

# Function to launch Plotly Dash app
def launch_dash_app(data):
    app = dash.Dash(__name__)

    # Prepare data for the graph
    timestamps = [row[0] for row in data]
    x_values = [row[1] for row in data]
    y_values = [row[2] for row in data]
    z_values = [row[3] for row in data]

    app.layout = html.Div(children=[
        html.H1(children='Accelerometer Data Plot'),
        dcc.Graph(
            id='accelerometer-graph',
            figure={
                'data': [
                    go.Scatter(x=timestamps, y=x_values, mode='lines', name='py_x'),
                    go.Scatter(x=timestamps, y=y_values, mode='lines', name='py_y'),
                    go.Scatter(x=timestamps, y=z_values, mode='lines', name='py_z')
                ],
                'layout': go.Layout(
                    title='Accelerometer Data Over Time (Last 10 Samples)',
                    xaxis={'title': 'Timestamp'},
                    yaxis={'title': 'Accelerometer Values'},
                )
            }
        )
    ])

    # Launch the Dash app in a new thread to allow real-time data capturing to continue
    threading.Thread(target=lambda: app.run_server(debug=False, use_reloader=False)).start()

def main():
    print("Starting main() function")

    try:
        # Instantiate Arduino cloud client
        client = ArduinoCloudClient(
            device_id=DEVICE_ID, username=DEVICE_ID, password=SECRET_KEY
        )

        # Register with 'py_x', 'py_y', and 'py_z' cloud variables
        client.register(
            "py_x", value=None, 
            on_write=lambda client, value: on_value_changed(client, "py_x", value)
        )
        client.register(
            "py_y", value=None, 
            on_write=lambda client, value: on_value_changed(client, "py_y", value)
        )
        client.register(
            "py_z", value=None, 
            on_write=lambda client, value: on_value_changed(client, "py_z", value)
        )

        # Start cloud client
        client.start()
    except Exception as e:
        print(f"Error in main(): {e}")

if __name__ == "__main__":
    try:
        main()  # main function which runs in an internal infinite loop
    except Exception as e:
        print(f"Unhandled exception: {e}")
    finally:
        # Close the CSV files
        all_data_file.close()
        plot_data_file.close()
