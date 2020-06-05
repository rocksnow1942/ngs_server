import re
from flask import current_app
from app.models import Slide, PPT, Project
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
from pptx import Presentation
from app import create_app
from app import db
from dateutil import parser
import hashlib
import sys
from pathlib import PurePath
import os
import time
from datetime import datetime, timedelta
