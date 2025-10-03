import random

import math
import time
import threading
import pygame

import sys
import os

# CNN Model Parameters
defaultRed = 150
defaultYellow = 5
defaultGreen = 20
defaultMinimum = 10
defaultMaximum = 60

signals = []
noOfSignals = 4
simTime = 300       # Simulation time in seconds
timeElapsed = 0

currentGreen = 0   # Current green signal index
nextGreen = (currentGreen+1)%noOfSignals
currentYellow = 0   # Yellow signal status 

# Vehicle passing times
carTime = 1
bikeTime = 1
ambulanceTime = 1.25  # Faster passing for ambulances
busTime = 1
truckTime = 1

# Vehicle counts
noOfCars = 0
noOfBikes = 0
noOfBuses = 0
noOfTrucks = 0
noOfAmbulances = 0
noOfLanes = 3  # Including ambulance lane

# Detection time
detectionTime = 5

# Vehicle speeds (ambulances are fastest)
speeds = {'car': 3, 'bus': 3, 'truck': 3, 'ambulance': 4.0, 'bike': 3}  

# Coordinates (added ambulance lane as lane 0)
x = {'right': [0, 0, 0, 0], 'down': [755, 727, 697, 667], 'left': [1400, 1400, 1400, 1400], 'up': [602, 627, 657, 687]}    
y = {'right': [350, 370, 400, 420], 'down': [0, 0, 0, 0], 'left': [500, 470, 430, 400], 'up': [800, 800, 800, 800]}

# Vehicle storage (added ambulance lane as lane 0)
vehicles = {
    'right': {0: [], 1: [], 2: [], 3: [], 'crossed': 0, 'ambulance_present': False}, 
    'down': {0: [], 1: [], 2: [], 3: [], 'crossed': 0, 'ambulance_present': False}, 
    'left': {0: [], 1: [], 2: [], 3: [], 'crossed': 0, 'ambulance_present': False}, 
    'up': {0: [], 1: [], 2: [], 3: [], 'crossed': 0, 'ambulance_present': False}
}

vehicleTypes = {0: 'car', 1: 'bus', 2: 'truck', 3: 'ambulance', 4: 'bike'}
directionNumbers = {0: 'right', 1: 'down', 2: 'left', 3: 'up'}

# Coordinates for UI elements
signalCoods = [(530,230), (810,230), (810,570), (530,570)]
signalTimerCoods = [(530,210), (810,210), (810,550), (530,550)]
vehicleCountCoods = [(480,210), (880,210), (880,550), (480,550)]
vehicleCountTexts = ["0", "0", "0", "0"]

# Stop lines
stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
defaultStop = {'right': [580, 580, 580, 580], 'down': [320, 320, 320, 320], 'left': [810, 810, 810, 810], 'up': [545, 545, 545, 545]}
stops = {'right': [580, 580, 580, 580], 'down': [320, 320, 320, 320], 'left': [810, 810, 810, 810], 'up': [545, 545, 545, 545]}

mid = {'right': {'x':705, 'y':445}, 'down': {'x':695, 'y':450}, 'left': {'x':695, 'y':425}, 'up': {'x':695, 'y':400}}
rotationAngle = 3

# Gap between vehicles
gap = 15    # Normal stopping gap
gap2 = 15   # Moving gap
ambulanceGap = 30  # Extra gap for ambulances

pygame.init()
simulation = pygame.sprite.Group()

class TrafficSignal:
    def __init__(self, red, yellow, green, minimum, maximum):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.minimum = minimum
        self.maximum = maximum
        self.signalText = "30"
        self.totalGreenTime = 0
        self.ambulancePriority = False
        self.originalGreen = green  # Store original green time
        self.originalRed = red      # Store original red time
        
class Vehicle(pygame.sprite.Sprite):
    def __init__(self, lane, vehicleClass, direction_number, direction, will_turn):
        pygame.sprite.Sprite.__init__(self)
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.speed = speeds[vehicleClass]
        self.direction_number = direction_number
        self.direction = direction
        self.x = x[direction][lane]
        self.y = y[direction][lane]
        self.crossed = 0
        self.willTurn = will_turn
        self.turned = 0
        self.rotateAngle = 0
        vehicles[direction][lane].append(self)
        self.index = len(vehicles[direction][lane]) - 1
        path = "images/" + direction + "/" + vehicleClass + ".png"
        self.originalImage = pygame.image.load(path)
        self.currentImage = pygame.image.load(path)
        
        # Set ambulance flag
        if vehicleClass == 'ambulance':
            vehicles[direction]['ambulance_present'] = True
            # Play siren sound when ambulance spawns
            if random.randint(1, 1) == 1:
                pygame.mixer.init()
                pygame.mixer.music.load("ambulance.mp3")
                pygame.mixer.music.play()
            # Activate emergency protocol
            activate_emergency_protocol(direction_number)

        # Set stop positions based on vehicle type
        if direction == 'right':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop - vehicles[direction][lane][self.index-1].currentImage.get_rect().width - (ambulanceGap if vehicleClass == 'ambulance' else gap)
            else:
                self.stop = defaultStop[direction][lane]
            temp = self.currentImage.get_rect().width + (ambulanceGap if vehicleClass == 'ambulance' else gap)
            x[direction][lane] -= temp
            stops[direction][lane] -= temp
            
        elif direction == 'left':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop + vehicles[direction][lane][self.index-1].currentImage.get_rect().width + (ambulanceGap if vehicleClass == 'ambulance' else gap)
            else:
                self.stop = defaultStop[direction][lane]
            temp = self.currentImage.get_rect().width + (ambulanceGap if vehicleClass == 'ambulance' else gap)
            x[direction][lane] += temp
            stops[direction][lane] += temp
            
        elif direction == 'down':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop - vehicles[direction][lane][self.index-1].currentImage.get_rect().height - (ambulanceGap if vehicleClass == 'ambulance' else gap)
            else:
                self.stop = defaultStop[direction][lane]
            temp = self.currentImage.get_rect().height + (ambulanceGap if vehicleClass == 'ambulance' else gap)
            y[direction][lane] -= temp
            stops[direction][lane] -= temp
            
        elif direction == 'up':
            if len(vehicles[direction][lane]) > 1 and vehicles[direction][lane][self.index-1].crossed == 0:
                self.stop = vehicles[direction][lane][self.index-1].stop + vehicles[direction][lane][self.index-1].currentImage.get_rect().height + (ambulanceGap if vehicleClass == 'ambulance' else gap)
            else:
                self.stop = defaultStop[direction][lane]
            temp = self.currentImage.get_rect().height + (ambulanceGap if vehicleClass == 'ambulance' else gap)
            y[direction][lane] += temp
            stops[direction][lane] += temp
            
        simulation.add(self)

    def render(self, screen):
        screen.blit(self.currentImage, (self.x, self.y))

    def move(self):
        is_ambulance = self.vehicleClass == 'ambulance'
        front_vehicle = None
        if self.index > 0:
            front_vehicle = vehicles[self.direction][self.lane][self.index-1]
        
        # Emergency mode for ambulances
        if is_ambulance:
            # Make other vehicles yield to ambulance
            for lane in range(noOfLanes):
                for vehicle in vehicles[self.direction][lane]:
                    if vehicle != self and not vehicle.crossed and vehicle.vehicleClass != 'ambulance':
                        # Slow down other vehicles in the same direction
                        if self.direction in ['right', 'left']:
                            if abs(vehicle.x - self.x) < 250:  # Larger detection range
                                vehicle.speed = (vehicle.speed)  # Slow down more
                        else:
                            if abs(vehicle.y - self.y) < 250:
                                vehicle.speed = ( vehicle.speed )
        
        if self.direction == 'right':
            if self.crossed == 0 and self.x + self.currentImage.get_rect().width > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
                if is_ambulance:
                    vehicles[self.direction]['ambulance_present'] = False
                    # Restore normal signal timing after ambulance passes
                    restore_normal_signal()
                    
            # Ambulance movement (priority)
            if is_ambulance:
                self.x += self.speed
                # Push vehicles in front if needed
                if front_vehicle and not front_vehicle.crossed and self.x + self.currentImage.get_rect().width > front_vehicle.x - gap2:
                    front_vehicle.x += 3  # Stronger push for ambulances
            else:
                # Normal vehicle movement
                can_move = (self.x + self.currentImage.get_rect().width <= self.stop or 
                            self.crossed == 1 or 
                            (currentGreen == self.direction_number and currentYellow == 0))
                
                space_in_front = True
                if front_vehicle and not front_vehicle.crossed:
                    space_in_front = (self.x + self.currentImage.get_rect().width < front_vehicle.x - gap2)
                
                if can_move and (self.index == 0 or space_in_front or (front_vehicle and front_vehicle.turned == 1)):
                    self.x += self.speed
                    
        elif self.direction == 'left':
            if self.crossed == 0 and self.x < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
                if is_ambulance:
                    vehicles[self.direction]['ambulance_present'] = False
                    restore_normal_signal()
                    
            if is_ambulance:
                self.x -= self.speed
                if front_vehicle and not front_vehicle.crossed and self.x < front_vehicle.x + front_vehicle.currentImage.get_rect().width + gap2:
                    front_vehicle.x -= 3
            else:
                can_move = (self.x >= self.stop or 
                           self.crossed == 1 or 
                           (currentGreen == self.direction_number and currentYellow == 0))
                space_in_front = True
                if front_vehicle and not front_vehicle.crossed:
                    space_in_front = (self.x > front_vehicle.x + front_vehicle.currentImage.get_rect().width + gap2)
                
                if can_move and (self.index == 0 or space_in_front or (front_vehicle and front_vehicle.turned == 1)):
                    self.x -= self.speed
                    
        elif self.direction == 'down':
            if self.crossed == 0 and self.y + self.currentImage.get_rect().height > stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
                if is_ambulance:
                    vehicles[self.direction]['ambulance_present'] = False
                    restore_normal_signal()
                    
            if is_ambulance:
                self.y += self.speed
                if front_vehicle and not front_vehicle.crossed and self.y + self.currentImage.get_rect().height > front_vehicle.y - gap2:
                    front_vehicle.y += 3
            else:
                can_move = (self.y + self.currentImage.get_rect().height <= self.stop or 
                           self.crossed == 1 or 
                           (currentGreen == self.direction_number and currentYellow == 0))
                space_in_front = True
                if front_vehicle and not front_vehicle.crossed:
                    space_in_front = (self.y + self.currentImage.get_rect().height < front_vehicle.y - gap2)
                
                if can_move and (self.index == 0 or space_in_front or (front_vehicle and front_vehicle.turned == 1)):
                    self.y += self.speed
                    
        elif self.direction == 'up':
            if self.crossed == 0 and self.y < stopLines[self.direction]:
                self.crossed = 1
                vehicles[self.direction]['crossed'] += 1
                if is_ambulance:
                    vehicles[self.direction]['ambulance_present'] = False
                    restore_normal_signal()
                    
            if is_ambulance:
                self.y -= self.speed
                if front_vehicle and not front_vehicle.crossed and self.y < front_vehicle.y + front_vehicle.currentImage.get_rect().height + gap2:
                    front_vehicle.y -= 3
            else:
                can_move = (self.y >= self.stop or 
                           self.crossed == 1 or 
                           (currentGreen == self.direction_number and currentYellow == 0))
                space_in_front = True
                if front_vehicle and not front_vehicle.crossed:
                    space_in_front = (self.y > front_vehicle.y + front_vehicle.currentImage.get_rect().height + gap2)
                
                if can_move and (self.index == 0 or space_in_front or (front_vehicle and front_vehicle.turned == 1)):
                    self.y -= self.speed

def activate_emergency_protocol(ambulance_direction):
    """Turn all signals red except the ambulance's direction"""
    global currentGreen, currentYellow
    
    # Store current signal states if not already in emergency
    if not any(signal.ambulancePriority for signal in signals):
        for signal in signals:
            signal.originalGreen = signal.green
            signal.originalRed = signal.red
    
    # Set all signals to red except the ambulance's direction
    for i in range(noOfSignals):
        if i == ambulance_direction:
            signals[i].green = defaultMaximum
            signals[i].red = 0
            signals[i].ambulancePriority = True
            currentGreen = i
            currentYellow = 0
        else:
            signals[i].green = 0
            signals[i].red = defaultMaximum
            signals[i].ambulancePriority = False
    
    os.system(f"say Emergency vehicle detected. Activating priority route.")

def restore_normal_signal():
    """Restore normal signal timing after ambulance passes"""
    # Check if any ambulance is still present in any direction
    for direction in ['right', 'left', 'up', 'down']:
        if vehicles[direction]['ambulance_present']:
            return  # Don't restore yet if another ambulance is present
    
    # Only restore if we're currently in emergency mode
    if any(signal.ambulancePriority for signal in signals):
        os.system("say Resuming normal traffic flow.")
        
        # Find which direction had priority
        for i in range(noOfSignals):
            if signals[i].ambulancePriority:
                signals[i].green = signals[i].originalGreen
                signals[i].red = signals[i].originalRed
                signals[i].ambulancePriority = False
                
                # Set the next green signal to be the one after the emergency direction
                global currentGreen, nextGreen
                currentGreen = i
                nextGreen = (currentGreen + 1) % noOfSignals
                
                # Update other signals
                for j in range(noOfSignals):
                    if j != currentGreen:
                        signals[j].red = signals[currentGreen].green + signals[currentGreen].yellow
                        signals[j].green = defaultGreen
                        signals[j].yellow = defaultYellow
                break

def initialize():
    ts1 = TrafficSignal(0, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts1)
    ts2 = TrafficSignal(ts1.red+ts1.yellow+ts1.green, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts2)
    ts3 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts3)
    ts4 = TrafficSignal(defaultRed, defaultYellow, defaultGreen, defaultMinimum, defaultMaximum)
    signals.append(ts4)
    repeat()

def setTime():
    global noOfCars, noOfBikes, noOfBuses, noOfTrucks, noOfAmbulances, noOfLanes
    global currentGreen, nextGreen
    
    # Skip timing adjustment if we're in emergency mode
    if any(signal.ambulancePriority for signal in signals):
        return
    
    # Check for ambulances first - give them priority
    for i in range(noOfSignals):
        direction = directionNumbers[i]
        if vehicles[direction]['ambulance_present']:
            nextGreen = i
            signals[nextGreen].green = defaultMaximum  # Max time to clear ambulance
            signals[nextGreen].ambulancePriority = True
            os.system(f"say Emergency vehicle detected in {direction} direction. Prioritizing route.")
            return
    
    # No ambulances found, proceed with normal timing
    os.system("say detecting vehicles, "+directionNumbers[(currentGreen+1)%noOfSignals])
    noOfCars, noOfBuses, noOfTrucks, noOfAmbulances, noOfBikes = 0, 0, 0, 0, 0
    
    # Count vehicles in the next green direction
    next_dir = directionNumbers[nextGreen]
    for j in range(len(vehicles[next_dir][0])):  # Ambulance lane
        vehicle = vehicles[next_dir][0][j]
        if vehicle.crossed == 0 and vehicle.vehicleClass == 'ambulance':
            noOfAmbulances += 1
            
    for i in range(1, noOfLanes):  # Other lanes
        for j in range(len(vehicles[next_dir][i])):
            vehicle = vehicles[next_dir][i][j]
            if vehicle.crossed == 0:
                vclass = vehicle.vehicleClass
                if vclass == 'car':
                    noOfCars += 1
                elif vclass == 'bus':
                    noOfBuses += 1
                elif vclass == 'truck':
                    noOfTrucks += 1
                elif vclass == 'bike':
                    noOfBikes += 1
    
    # Calculate green time
    greenTime = math.ceil((
        (noOfCars * carTime) + 
        (noOfAmbulances * ambulanceTime) + 
        (noOfBuses * busTime) + 
        (noOfTrucks * truckTime) + 
        (noOfBikes * bikeTime))
    ) / (noOfLanes + 1)
    
    print('Green Time: ', greenTime)
    if greenTime < defaultMinimum:
        greenTime = defaultMinimum
    elif greenTime > defaultMaximum:
        greenTime = defaultMaximum
        
    signals[nextGreen].green = greenTime
    signals[nextGreen].ambulancePriority = False

def repeat():
    global currentGreen, currentYellow, nextGreen
    while signals[currentGreen].green > 0:
        printStatus()
        updateValues()
        if signals[(currentGreen+1)%noOfSignals].red == detectionTime:
            thread = threading.Thread(name="detection", target=setTime, args=())
            thread.daemon = True
            thread.start()
        time.sleep(1)
        
    currentYellow = 1
    vehicleCountTexts[currentGreen] = "0"
    
    # Reset stop coordinates
    for i in range(noOfLanes):
        stops[directionNumbers[currentGreen]][i] = defaultStop[directionNumbers[currentGreen]][i]
        for vehicle in vehicles[directionNumbers[currentGreen]][i]:
            vehicle.stop = defaultStop[directionNumbers[currentGreen]][i]
    
    while signals[currentGreen].yellow > 0:
        printStatus()
        updateValues()
        time.sleep(1)
        
    currentYellow = 0
    
    # Skip normal signal rotation if we're in emergency mode
    if not any(signal.ambulancePriority for signal in signals):
        signals[currentGreen].green = defaultGreen
        signals[currentGreen].yellow = defaultYellow
        signals[currentGreen].red = defaultRed
        currentGreen = nextGreen
        nextGreen = (currentGreen+1) % noOfSignals
        signals[nextGreen].red = signals[currentGreen].yellow + signals[currentGreen].green
    
    repeat()

def printStatus():
    for i in range(noOfSignals):
        if i == currentGreen:
            if currentYellow == 0:
                print("GREEN TS", i+1, "-> r:", signals[i].red, " y:", signals[i].yellow, " g:", signals[i].green)
            else:
                print("YELLOW TS", i+1, "-> r:", signals[i].red, " y:", signals[i].yellow, " g:", signals[i].green)
        else:
            print("RED TS", i+1, "-> r:", signals[i].red, " y:", signals[i].yellow, " g:", signals[i].green)
    print()

def updateValues():
    for i in range(noOfSignals):
        if i == currentGreen:
            if currentYellow == 0:
                signals[i].green -= 1
                signals[i].totalGreenTime += 1
            else:
                signals[i].yellow -= 1
        else:
            signals[i].red -= 1

def generateVehicles():
    # Parameters for ambulance frequency
    ambulance_spawn_chance = 0.15  # 15% chance each spawn attempt
    min_ambulance_delay = 5  # seconds
    max_ambulance_delay = 8  # seconds
    
    while True:
        # First decide if this will be an ambulance
        spawn_ambulance = random.random() < ambulance_spawn_chance
        
        if spawn_ambulance:
            # Spawn an ambulance
            vehicle_type = 3  # Ambulance
            lane_number = 0  # Always in ambulance lane
            
            # Random direction for ambulance
            direction_number = random.randint(0, 3)
            direction = directionNumbers[direction_number]
            
            # Ambulances don't turn in this simulation
            will_turn = 0
            
            # Create the ambulance
            Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, direction, will_turn)
            
            # Wait before next ambulance (random delay)
            time.sleep(random.uniform(min_ambulance_delay, max_ambulance_delay))
        else:
            # Spawn a normal vehicle
            vehicle_type = random.choice([0, 1, 2, 4])  # car, bus, truck, bike
            
            # Assign lane - bikes in lane 1, others in lanes 1-2
            if vehicle_type == 4:  # Bike
                lane_number = 1
            else:  # Car, bus, truck
                lane_number = random.randint(1, 2)
                
            will_turn = 0
            if lane_number == 2:
                will_turn = random.randint(0, 2) <= 1  # 50% chance to turn
                
            # Random direction
            temp = random.randint(0, 999)
            direction_number = 0
            a = [400, 800, 900, 1000]
            if temp < a[0]:
                direction_number = 0
            elif temp < a[1]:
                direction_number = 1
            elif temp < a[2]:
                direction_number = 2
            elif temp < a[3]:
                direction_number = 3
                
            Vehicle(lane_number, vehicleTypes[vehicle_type], direction_number, directionNumbers[direction_number], will_turn)
            
            # Normal vehicle spawn delay
            time.sleep(random.uniform(0.5, 1))

def simulationTime():
    global timeElapsed, simTime
    while True:
        timeElapsed += 1
        time.sleep(1)
        if timeElapsed == simTime:
            totalVehicles = 0
            totalAmbulances = 0
            print('Lane-wise Vehicle Counts')
            for i in range(noOfSignals):
                print('Lane', i+1, ':', vehicles[directionNumbers[i]]['crossed'])
                totalVehicles += vehicles[directionNumbers[i]]['crossed']
                
                # Count ambulances separately
                for lane in range(noOfLanes):
                    for vehicle in vehicles[directionNumbers[i]][lane]:
                        if vehicle.vehicleClass == 'ambulance':
                            totalAmbulances += 1
            
            print('\nTotal vehicles passed:', totalVehicles)
            print('Total ambulances passed:', totalAmbulances)
            print('Total time passed:', timeElapsed, 'seconds')
            print('Vehicles per minute:', (float(totalVehicles)/float(timeElapsed))*60)
            print('Ambulances per minute:', (float(totalAmbulances)/float(timeElapsed))*60)
            os._exit(1)

class Main:
    thread4 = threading.Thread(name="simulationTime", target=simulationTime, args=()) 
    thread4.daemon = True
    thread4.start()

    thread2 = threading.Thread(name="initialization", target=initialize, args=())
    thread2.daemon = True
    thread2.start()

    # Colors
    black = (0, 0, 0)
    white = (255, 255, 255)
    red = (255, 0, 0)
    green = (0, 255, 0)
    blue = (0, 0, 255)
    yellow = (255, 255, 0)

    # Screen size
    screenWidth = 1400
    screenHeight = 800
    screenSize = (screenWidth, screenHeight)

    # Background
    background = pygame.image.load('images/mod_int.png')

    screen = pygame.display.set_mode(screenSize)
    pygame.display.set_caption("Emergency Traffic Simulation - Frequent Ambulances")

    # Signals
    redSignal = pygame.image.load('images/signals/red.png')
    yellowSignal = pygame.image.load('images/signals/yellow.png')
    greenSignal = pygame.image.load('images/signals/green.png')
    font = pygame.font.Font(None, 30)
    boldFont = pygame.font.Font(None, 40)
    largeFont = pygame.font.Font(None, 60)

    thread3 = threading.Thread(name="generateVehicles", target=generateVehicles, args=())
    thread3.daemon = True
    thread3.start()

    # Ambulance spawn timer
    last_ambulance_time = time.time()
    ambulance_spawn_interval = random.uniform(5, 15)  # Random interval between 5-15 seconds

    while True:
        current_time = time.time()
        
        # Check if it's time to spawn an ambulance
        if current_time - last_ambulance_time > ambulance_spawn_interval:
            # Reset timer with new random interval
            last_ambulance_time = current_time
            ambulance_spawn_interval = random.uniform(5, 15)
            
            # 50% chance to spawn an ambulance
            if random.random() < 0.5:
                # Spawn ambulance in random direction
                direction_number = random.randint(0, 3)
                Vehicle(0, 'ambulance', direction_number, directionNumbers[direction_number], 0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        screen.blit(background, (0, 0))
        
        # Draw ambulance lane markers (thicker and more visible)
        for direction in ['right', 'left', 'up', 'down']:
            if direction == 'right':
                pygame.draw.line(screen, blue, (0, y[direction][0] - 15), (stopLines[direction], y[direction][0] - 15), 5)
                # Draw ambulance symbol
                ambulance_icon = largeFont.render("A", True, white, blue)
                screen.blit(ambulance_icon, (50, y[direction][0] - 30))
            elif direction == 'left':
                pygame.draw.line(screen, blue, (stopLines[direction], y[direction][0] - 15), (screenWidth, y[direction][0] - 15), 5)
                ambulance_icon = largeFont.render("A", True, white, blue)
                screen.blit(ambulance_icon, (screenWidth - 80, y[direction][0] - 30))
            elif direction == 'down':
                pygame.draw.line(screen, blue, (x[direction][0] - 15, 0), (x[direction][0] - 15, stopLines[direction]), 5)
                ambulance_icon = largeFont.render("A", True, white, blue)
                screen.blit(ambulance_icon, (x[direction][0] - 30, 50))
            elif direction == 'up':
                pygame.draw.line(screen, blue, (x[direction][0] - 15, stopLines[direction]), (x[direction][0] - 15, screenHeight), 5)
                ambulance_icon = largeFont.render("A", True, white, blue)
                screen.blit(ambulance_icon, (x[direction][0] - 30, screenHeight - 80))
        
        # Display signals
        for i in range(noOfSignals):
            if i == currentGreen:
                if currentYellow == 1:
                    signals[i].signalText = signals[i].yellow if signals[i].yellow != 0 else "STOP"
                    screen.blit(yellowSignal, signalCoods[i])
                else:
                    signals[i].signalText = signals[i].green if signals[i].green != 0 else "SLOW"
                    screen.blit(greenSignal, signalCoods[i])
            else:
                if signals[i].red <= 10:
                    signals[i].signalText = signals[i].red if signals[i].red != 0 else "GO"
                else:
                    signals[i].signalText = "---"
                screen.blit(redSignal, signalCoods[i])
        
        # Display signal timers and vehicle counts
        for i in range(noOfSignals):
            signalTexts = font.render(str(signals[i].signalText), True, white, black)
            screen.blit(signalTexts, signalTimerCoods[i])
            
            # Highlight if ambulance is present
            if vehicles[directionNumbers[i]]['ambulance_present']:
                text = boldFont.render("EMS!", True, red, yellow)
                screen.blit(text, (vehicleCountCoods[i][0], vehicleCountCoods[i][1] - 30))
                # Flash the text
                if int(time.time()) % 2 == 0:
                    pygame.draw.circle(screen, red, (vehicleCountCoods[i][0] - 20, vehicleCountCoods[i][1] - 10), 10)
            
            displayText = vehicles[directionNumbers[i]]['crossed']
            vehicleCountTexts[i] = font.render(str(displayText), True, black, white)
            screen.blit(vehicleCountTexts[i], vehicleCountCoods[i])

        # Display simulation info
        timeElapsedText = font.render(f"Time: {timeElapsed}s", True, black, white)
        screen.blit(timeElapsedText, (1100, 50))
        
        # Display ambulance counter
        total_ambulances = 0
        for direction in ['right', 'left', 'up', 'down']:
            for lane in range(noOfLanes):
                for vehicle in vehicles[direction][lane]:
                    if vehicle.vehicleClass == 'ambulance':
                        total_ambulances += 1
        ambulanceText = font.render(f"Ambulances: {total_ambulances}", True, red, white)
        screen.blit(ambulanceText, (1100, 80))
        
        # Display vehicles
        for vehicle in simulation:
            screen.blit(vehicle.currentImage, [vehicle.x, vehicle.y])
            vehicle.move()
            
            # Highlight ambulances with flashing border
            if vehicle.vehicleClass == 'ambulance':
                if int(time.time() * 2) % 2 == 0:  # Flash twice per second
                    pygame.draw.rect(screen, red, (vehicle.x - 3, vehicle.y - 3, 
                                    vehicle.currentImage.get_rect().width + 6, 
                                    vehicle.currentImage.get_rect().height + 6), 3)
        
        pygame.display.update()

Main()