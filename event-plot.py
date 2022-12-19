import datetime as dt
import sys
import time

import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Create figure for plotting
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
xs = []
ys = []

# Initialize communication with TMP102
def read_data():
    data = None
    while data is None:
        while True:
            start = time.time_ns()
            line = sys.stdin.readline()
            if time.time_ns() > start + 1_000_000:
                break
        if line.startswith("EVENT_DATA ABS_X"):
            data = float(line.split(" ")[-2])
            print(line.split(" "), data)
            return data

# This function is called periodically from FuncAnimation
def animate(i, xs, ys):

    # Read temperature (Celsius) from TMP102
    temp_c = read_data()

    # Add x and y to lists
    xs.append(dt.datetime.now().strftime('%H:%M:%S.%f'))
    ys.append(temp_c)

    # Limit x and y lists to 20 items
    xs = xs[-200:]
    ys = ys[-200:]

    # Draw x and y lists
    ax.clear()
    ax.plot(xs, ys)

    # Format plot
    #plt.xticks(rotation=45, ha='right')
    plt.subplots_adjust(bottom=0.30)
    plt.title('TMP102 Temperature over Time')
    plt.ylabel('Temperature (deg C)')

# Set up plot to call animate() function periodically
ani = animation.FuncAnimation(fig, animate, fargs=(xs, ys), interval=50)
plt.show()
