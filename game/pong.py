import cv2
import random
from ultralytics import YOLO

# Load the YOLOv8 pose TensorRT engine
# Ultralytics handles the .engine format seamlessly as long as your TensorRT environment is set up.
model = YOLO("temp/yolo11n-pose.engine", task="pose")

# Initialize Webcam
cap = cv2.VideoCapture(0)
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Game Variables
paddle_width = 15
paddle_height = 100
player_score = 0
robot_score = 0

# Player Paddle (Left)
player_x = 30
player_y = frame_height // 2 - paddle_height // 2

# Robot Paddle (Right)
robot_x = frame_width - 30 - paddle_width
robot_y = frame_height // 2 - paddle_height // 2
robot_speed = 7

# Ball
ball_size = 15
ball_x = frame_width // 2
ball_y = frame_height // 2
ball_speed_x = 8 * random.choice([-1, 1])
ball_speed_y = 8 * random.choice([-1, 1])


def reset_ball():
    global ball_x, ball_y, ball_speed_x, ball_speed_y
    ball_x = frame_width // 2
    ball_y = frame_height // 2
    ball_speed_x = 8 * random.choice([-1, 1])
    ball_speed_y = 8 * random.choice([-1, 1])


while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("Ignoring empty camera frame.")
        continue

    # Flip the frame horizontally for a natural selfie-view
    frame = cv2.flip(frame, 1)

    # 1. Pose Tracking with YOLOv8 TensorRT
    # We set verbose=False to stop YOLO from printing detection stats to the console every frame
    results = model(frame, verbose=False)

    # Check if at least one person is detected
    if len(results[0]) > 0 and results[0].keypoints is not None:
        # Extract the keypoints for the first person detected [xy coordinates, moved to CPU as numpy array]
        keypoints = results[0].keypoints.xy.cpu().numpy()[0]
        
        # YOLOv8 COCO Keypoints: 9 is Left Wrist, 10 is Right Wrist
        # Let's try to use the right wrist first
        right_wrist_y = keypoints[10][1]
        left_wrist_y = keypoints[9][1]

        # Use right wrist if visible (Y > 0), otherwise fallback to left wrist
        if right_wrist_y > 0:
            target_y = right_wrist_y
        elif left_wrist_y > 0:
            target_y = left_wrist_y
        else:
            target_y = None

        if target_y is not None:
            player_y = int(target_y) - (paddle_height // 2)

    # Keep player paddle on screen
    player_y = max(0, min(player_y, frame_height - paddle_height))

    # 2. Robot (AI) Movement
    robot_center = robot_y + (paddle_height // 2)
    if robot_center < ball_y - 15:
        robot_y += robot_speed
    elif robot_center > ball_y + 15:
        robot_y -= robot_speed

    # Keep robot paddle on screen
    robot_y = max(0, min(robot_y, frame_height - paddle_height))

    # 3. Ball Physics & Movement
    ball_x += ball_speed_x
    ball_y += ball_speed_y

    # Bounce off top and bottom walls
    if ball_y <= 0 or ball_y >= frame_height - ball_size:
        ball_speed_y *= -1

    # Collisions with Player Paddle
    if ball_x <= player_x + paddle_width:
        if player_y <= ball_y <= player_y + paddle_height:
            ball_speed_x *= -1
            ball_speed_x *= 1.05
            ball_speed_y *= 1.05

    # Collisions with Robot Paddle
    if ball_x >= robot_x - ball_size:
        if robot_y <= ball_y <= robot_y + paddle_height:
            ball_speed_x *= -1
            ball_speed_x *= 1.05
            ball_speed_y *= 1.05

    # Scoring
    if ball_x < 0:
        robot_score += 1
        reset_ball()
    elif ball_x > frame_width:
        player_score += 1
        reset_ball()

    # 4. Drawing the Game Elements
    # Optionally, draw the skeleton to see what YOLO is tracking
    # annotated_frame = results[0].plot() # Uncomment this to see the YOLO skeleton overlaid!
    annotated_frame = frame 

    # Draw Player Paddle (Green)
    cv2.rectangle(
        annotated_frame,
        (player_x, player_y),
        (player_x + paddle_width, player_y + paddle_height),
        (0, 255, 0),
        -1,
    )

    # Draw Robot Paddle (Red)
    cv2.rectangle(
        annotated_frame,
        (robot_x, robot_y),
        (robot_x + paddle_width, robot_y + paddle_height),
        (0, 0, 255),
        -1,
    )

    # Draw Ball (White)
    cv2.circle(annotated_frame, (int(ball_x), int(ball_y)), ball_size, (255, 255, 255), -1)

    # Draw Scores
    cv2.putText(
        annotated_frame,
        f"You: {player_score}",
        (50, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )
    cv2.putText(
        annotated_frame,
        f"Robot: {robot_score}",
        (frame_width - 200, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2,
    )

    # Display the result
    cv2.imshow("YOLOv8 TensorRT Pong", annotated_frame)

    # Press 'q' to quit the game
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()