#!/usr/bin/env python
# coding: utf-8
# Auteur    : Patrick Pinard
# Date      : 12.3.2014
# Objet     : Pilotage d'une voiture électrique "PiCar" avec interface web basée sur API RESTful Flask et Bootstrap
# Version   : 2  (ajout niveau du signal wifi et du niveau de batterie)

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
from WifiQualityChecker import WifiQualityChecker

global PiCar, state, battery, cpu_usage, signal

PASSWORD = "password"
USERNAME = "admin"

speed = 0.8
steering = 0.2

# fichier log
logging.basicConfig(
    filename="PiCar.log",
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
    """Generateur du streaming de la Camera."""
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


@app.route("/video_feed")
def video_feed():
    """Route pour le streaming de la Camera."""
    return Response(genFrames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/stats", methods=["GET", "POST"])
def stats():
    """Informations statistiques sur le PI et la Camera."""
    logging.info("lecture des statistiques")
    Wifi_Quality, Signal_level, Link_Quality = WifiQualityChecker("wlan0")
    stats = jsonify(
        {
            "CPU_percent": psutil.cpu_percent(),
            "CPU_temp": psutil.sensors_temperatures()["cpu_thermal"][0].current,
            "RAM_usage": psutil.virtual_memory().percent,
            "Wifi_quality": Wifi_Quality,
            "Signal_level": Signal_level,
            "Battery_level" : PiCar.battery(),
            "State": PiCar.running
        }
    )
    logging.info(stats)
    return statss


@app.route("/rtd")
def rtd():
    """Réponse pour calcul du Round Trip Delay : voiture -> interface web -> voiture (voir javascript)"""
    data = jsonify({"rtd": "OK"})
    return data


@app.route("/", methods=["GET", "POST"])
def home():
    """Route principale (home)"""
    global PiCar, cpu_usage, signal, battery, state, name, fast_turn, full_speed

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
    """Stop la voiture PiCar et logout"""
    global name
    PiCar.running = False
    logging.info("PiCar stopped when logout")
    session["logged_in"] = False
    logging.info("user " + name + " logout")
    return render_template("login.html")


@app.route("/startstop", methods=["GET", "POST"])
def startstop():
    global PiCar
    if session["logged_in"]:
        PiCar.running = not PiCar.running
        if PiCar.running:
            logging.info("Change state PiCar to START ")
        else:
            logging.info("Change state PiCar to STOP ")
        return ("", 204)
    else:
        return render_template("login.html")


@app.route("/speed", methods=["GET", "POST"])
def slow():
    global PiCar, speed
    logging.info(request)
    if session["logged_in"]:
        speed = request.args.get("speed")
        if speed == "slow":
            # PiCar.speedright = 0.4
            # PiCar.speedleft = 0.4
            speed = 0.4
            logging.info("Change speed to SLOW")

        if speed == "normal":
            # PiCar.speedright = 0.6
            # PiCar.speedleft = 0.6
            speed = 0.6
            logging.info("Change speed to NORMAL")

        if speed == "fast":
            # PiCar.speedright = 0.9
            # PiCar.speedleft = 0.9
            speed = 0.9
            logging.info("Change speed to FAST")
        PiCar.stop()
        PiCar.start()
        return ("", 204)
    else:
        return render_template("login.html")


@app.route("/left", methods=["GET", "POST"])
def left():
    global PiCar, speed

    if session["logged_in"]:
        method = request.args.get("method")
        if method == "stop":
            logging.info("Stop goes left ")
            PiCar.speedright = 0
            PiCar.speedleft = 0
        else:
            PiCar.speedright = speed
            PiCar.speedleft = -speed * (1 + steering)
            logging.info(
                "move right with speedright = "
                + str(PiCar.speedright)
                + "  speedleft = "
                + str(PiCar.speedleft)
            )
        return "OK"
    else:
        return render_template("login.html")


@app.route("/forward", methods=["GET", "POST"])
def forward():
    global PiCar, speed, steering

    if session["logged_in"]:
        method = request.args.get("method")
        if method == "stop":
            logging.info("Stop goes forward ")
            PiCar.speedright = 0
            PiCar.speedleft = 0
        else:
            PiCar.speedright = -speed
            PiCar.speedleft = -speed
            logging.info(
                "move forward with speedright = "
                + str(PiCar.speedright)
                + "  speedleft = "
                + str(PiCar.speedleft)
            )
        return "OK"
    else:
        return render_template("login.html")


@app.route("/backward", methods=["GET", "POST"])
def backward():
    global PiCar, speed, steering

    if session["logged_in"]:
        method = request.args.get("method")
        if method == "stop":
            logging.info("Stop forward ")
            PiCar.speedright = 0
            PiCar.speedleft = 0
        else:
            PiCar.speedright = speed
            PiCar.speedleft = speed
            logging.info(
                "move backward / speedright = "
                + str(PiCar.speedright)
                + "  speedleft = "
                + str(PiCar.speedleft)
            )
        return "OK"
    else:
        return render_template("login.html")


@app.route("/right", methods=["GET", "POST"])
def right():
    global PiCar, speed

    if session["logged_in"]:
        method = request.args.get("method")
        if method == "stop":
            logging.info("Stop goes right ")
            PiCar.speedright = 0
            PiCar.speedleft = 0
        else:
            PiCar.speedright = -speed * (1 + steering)
            PiCar.speedleft = speed
            logging.info(
                "move left / speedright = "
                + str(PiCar.speedright)
                + "  speedleft = "
                + str(PiCar.speedleft)
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


class MovePiCar(threading.Thread):
    global PiCar

    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

    def run(self):
        logging.info("MovePiCar Thread started")
        while True:
            try:
                while PiCar.running:
                    PiCar.move()
            except:
                logging.error("Move error in Thread")


if __name__ == "__main__":

    app.secret_key = os.urandom(12)

    # Create the PiCar car
    PiCar = carLib.car("PiCar")
    PiCar.start()

    # Create new threads
    thread1 = FlaskApp(1, "FlaskApp")
    thread2 = MovePiCar(2, "MovePiCar")

    # Start new Threads
    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    logging.info("Threads started and joined ....")
