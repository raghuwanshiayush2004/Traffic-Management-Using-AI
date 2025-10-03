from cProfile import label
import cv2
import os

# Directory and files
image_dir = "test_images1"
image_files = ["5.jpg", "6.jpg"]
match_threshold = 0.7  # Confidence threshold

img5 = cv2.imread(os.path.join(image_dir, "5.jpg"))
# Coordinates of the ambulance  (x, y, w, h)
x, y, w, h = 160, 300, 100, 80  # Adjusted from known ambulance 
template = img5[y:y+h, x:x+w]
template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

# Step 2: Function to auto-detect ambulance
def detect_ambulance(image_path):
    img = cv2.imread(image_path)
    label == 'ambulance' or label == 'ecnalubma' or label == 'AMBULANCE' or label == 'ECNALUBMA'
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    if max_val >= match_threshold:
        top_left = max_loc
        padding = 250  # Increased padding for a larger box
        bottom_right = (min(img.shape[1], top_left[0] + w + padding), 
                        min(img.shape[0], top_left[1] + h + padding))

        # Draw a thicker green rectangle (thickness = 5 for more visibility)
        cv2.rectangle(img, top_left, bottom_right, (0, 255, 0), thickness=5)

        # Label it "ambulance" above the box with a larger font size and thicker text
        cv2.putText(img, "ambulance", (top_left[0], top_left[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 4)

        print(f"✅ Ambulance detected in '{os.path.basename(image_path)}' (Score: {max_val:.2f})")
    else:
        print(f"❌ No ambulance detected in '{os.path.basename(image_path)}' (Score: {max_val:.2f})")

    # Display image for 2 seconds
    cv2.imshow(os.path.basename(image_path), img)
    cv2.waitKey(2000)
    cv2.destroyWindow(os.path.basename(image_path))

# Step 3: Run on both images
for filename in image_files:
    detect_ambulance(os.path.join(image_dir, filename))
