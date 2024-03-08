#!/usr/bin/env python
# coding: utf-8
# Auteur    : Patrick Pinard
# Date      : 9.3.2014
# Objet     : Pilotage de Monsterborg avec interface web basée sur API RESTful Flask et bootstrap
# Version   : 9
#
#  {} = "alt/option" + "(" ou ")"
#  [] = "alt/option" + "5" ou "6"
#   ~  = "alt/option" + n
#   \  = Alt + Maj + /


import io
import logging
import os
import threading
from threading import Condition

import carLib
import picamera2
import psutil
from flask import Flask, Response, jsonify, render_template, request, session
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput

global Borg, state, battery, cpu_usage, signal

PASSWORD = "password"
USERNAME = "admin"

speed = 0.8
steering = 0.2

# fichier log
logging.basicConfig(
    filename="app.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = Flask(__name__)


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


def genFrames():
    """Video streaming generator function."""
    with picamera2.Picamera2() as camera:

        output = StreamingOutput()
        # camera.configure(camera.create_video_configuration(main={"size": (640, 480)}))
        camera.configure(camera.create_video_configuration(main={"size": (1280, 720)}))
        # camera.configure(camera.create_video_configuration(main={"size": (1600, 1200)}))
        camera.options["compress_level"] = 2
        output = StreamingOutput()
        camera.start_recording(JpegEncoder(), FileOutput(output))

        while True:
            with output.condition:
                output.condition.wait()
                frame = output.frame
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")


# defines the route that will access the video feed and call the feed function
@app.route("/video_feed")
def video_feed():
    return Response(genFrames(), mimetype="multipart/x-mixed-replace; boundary=frame")


# statistiques du Raspberry Pi
@app.route("/stats", methods=["GET", "POST"])
def stats():
    """Provide system and camera stats."""
    logging.info("lecture des statistiques")
    stats = jsonify(
        {
            "cpu_percent": psutil.cpu_percent(),
            "cpu_temp": psutil.sensors_temperatures()["cpu_thermal"][0].current,
            "ram_usage": psutil.virtual_memory().percent,
        }
    )
    logging.info(stats)
    return stats


# réponse pour calcul du Round Trip Delay
@app.route("/rtd")
def rtd():
    """sent back OK to calculate Round Trip Delay in ms."""
    data = jsonify({"rtd": "OK"})
    return data


@app.route("/", methods=["GET", "POST"])
def home():

    global Borg, cpu_usage, signal, battery, state, name, fast_turn, full_speed

    if request.method == "GET":
        # Check if user already logged in
        logging.info("received a GET request")
        if not session.get("logged_in"):
            logging.info("login not done, redirect to 'login' page")
            return render_template("login.html", error_message="please login")
        else:
            logging.info("login already done, redirect to 'index' page")
            return "already logged"

    if request.method == "POST":
        # Try to login user
        logging.info("received a POST request")
        name = request.form.get("username")
        pwd = request.form.get("password")

        if pwd == PASSWORD and name == USERNAME:
            logging.info("user: " + name + " logged in")
            session["logged_in"] = True
            return render_template("index.html")
        else:
            logging.warning("login with wrong username and password")
            return render_template(
                "login.html",
                error_message="wrong username and password. Please try again",
            )


@app.route("/shutdown", methods=["POST", "GET"])
def shutdown():
    if session["logged_in"]:
        logging.warning("shutdown requested by admin")
        os.system("sudo halt")
        return
    else:
        return render_template("login.html")


@app.route("/logout", methods=["POST", "GET"])
def logout():
    global name
    # stop the Monsterborg if logout
    Borg.running = False
    logging.info("Monsterborg stopped when logout")
    session["logged_in"] = False
    logging.info("user " + name + " logout")
    return render_template("login.html")


@app.route("/startstop", methods=["GET", "POST"])
def startstop():
    global Borg
    if session["logged_in"]:
        Borg.running = not Borg.running
        if Borg.running:
            logging.info("Change state MonsterBorg to START ")
        else:
            logging.info("Change state MonsterBorg to STOP ")
        return ("", 204)
    else:
        return render_template("login.html")


@app.route("/info", methods=["GET", "POST"])
def info():
    global Borg
    battery = Borg.battery()
    data = jsonify({"battery": battery, "state": Borg.running})
    logging.info(data)
    return data


# Utiliser pour pilotage par un autre device (smartphone) avec touch pad
@app.route("/control", methods=["GET", "POST"])
def control():
    if session["logged_in"]:
        return render_template("control.html")
    else:
        return render_template("login.html")


@app.route("/speed", methods=["GET", "POST"])
def slow():
    global Borg, speed
    logging.info(request)
    if session["logged_in"]:
        speed = request.args.get("speed")
        if speed == "slow":
            # Borg.speedright = 0.4
            # Borg.speedleft = 0.4
            speed = 0.4
            logging.info("Change speed to SLOW")

        if speed == "normal":
            # Borg.speedright = 0.6
            # Borg.speedleft = 0.6
            speed = 0.6
            logging.info("Change speed to NORMAL")

        if speed == "fast":
            # Borg.speedright = 0.9
            # Borg.speedleft = 0.9
            speed = 0.9
            logging.info("Change speed to FAST")
        Borg.stop()
        Borg.start()
        return ("", 204)
    else:
        return render_template("login.html")


@app.route("/left", methods=["GET", "POST"])
def left():
    global Borg, speed

    if session["logged_in"]:
        method = request.args.get("method")
        if method == "stop":
            logging.info("Stop goes left ")
            Borg.speedright = 0
            Borg.speedleft = 0
        else:
            Borg.speedright = speed
            Borg.speedleft = -speed * (1 + steering)
            logging.info(
                "move right with speedright = "
                + str(Borg.speedright)
                + "  speedleft = "
                + str(Borg.speedleft)
            )
        return "OK"
    else:
        return render_template("login.html")


@app.route("/forward", methods=["GET", "POST"])
def forward():
    global Borg, speed, steering

    if session["logged_in"]:
        method = request.args.get("method")
        if method == "stop":
            logging.info("Stop goes forward ")
            Borg.speedright = 0
            Borg.speedleft = 0
        else:
            Borg.speedright = -speed
            Borg.speedleft = -speed
            logging.info(
                "move forward with speedright = "
                + str(Borg.speedright)
                + "  speedleft = "
                + str(Borg.speedleft)
            )
        return "OK"
    else:
        return render_template("login.html")


@app.route("/backward", methods=["GET", "POST"])
def backward():
    global Borg, speed, steering

    if session["logged_in"]:
        method = request.args.get("method")
        if method == "stop":
            logging.info("Stop forward ")
            Borg.speedright = 0
            Borg.speedleft = 0
        else:
            Borg.speedright = speed
            Borg.speedleft = speed
            logging.info(
                "move backward / speedright = "
                + str(Borg.speedright)
                + "  speedleft = "
                + str(Borg.speedleft)
            )
        return "OK"
    else:
        return render_template("login.html")


@app.route("/right", methods=["GET", "POST"])
def right():
    global Borg, speed

    if session["logged_in"]:
        method = request.args.get("method")
        if method == "stop":
            logging.info("Stop goes right ")
            Borg.speedright = 0
            Borg.speedleft = 0
        else:
            Borg.speedright = -speed * (1 + steering)
            Borg.speedleft = speed
            logging.info(
                "move left / speedright = "
                + str(Borg.speedright)
                + "  speedleft = "
                + str(Borg.speedleft)
            )
        return "OK"
    else:
        return render_template("login.html")


class FlaskApp(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        logging.info("FlaskApp Thread started")
        app.run(host="0.0.0.0", port=80, debug=False)


class MoveBorg(threading.Thread):
    global Borg

    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        logging.info("MoveBorg Thread started")
        while True:
            try:
                while Borg.running:
                    Borg.move()
            except:
                logging.error("Move error in Thread")


if __name__ == "__main__":

    app.secret_key = os.urandom(12)

    # Create the MonsterBorg car
    Borg = carLib.car("MonsterBorg")
    Borg.start()

    # Create new threads
    thread1 = FlaskApp(1, "FlaskApp")
    thread2 = MoveBorg(2, "MoveBorg")

    # Start new Threads
    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    logging.info("Threads started and joined ....")
