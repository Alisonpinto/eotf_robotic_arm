"""
Test suite for Natural Language Command -> Object Matching Pipeline.
"""

from ai.interpreter import parse_command
from ai.schemas import StructuredTask
from vision.detector import DetectedObject, BoundingBox, Point2D
from vision.object_matcher import object_matcher, MatchEvaluation


def test_command_parsing():
    print("--- 1. Testing AI Command Parser (Dynamic NLP) ---")
    
    # Test 1: "Pick the red bottle."
    t1 = parse_command("Pick the red bottle.")
    assert t1.action == "pick"
    assert t1.object is not None
    assert t1.object.name == "bottle"
    assert t1.object.color == "red"
    print(f"[OK] 'Pick the red bottle.' -> action: '{t1.action}', object: '{t1.object.name}', color: '{t1.object.color}'")

    # Test 2: "Find the blue cup."
    t2 = parse_command("Find the blue cup.")
    assert t2.action == "find"
    assert t2.object is not None
    assert t2.object.name == "cup"
    assert t2.object.color == "blue"
    print(f"[OK] 'Find the blue cup.' -> action: '{t2.action}', object: '{t2.object.name}', color: '{t2.object.color}'")

    # Test 3: "Pick the mouse."
    t3 = parse_command("Pick the mouse.")
    assert t3.action == "pick"
    assert t3.object is not None
    assert t3.object.name == "mouse"
    assert t3.object.color is None
    print(f"[OK] 'Pick the mouse.' -> action: '{t3.action}', object: '{t3.object.name}', color: {t3.object.color}")

    # Test 4: "Take the green bottle and give it to the JetArm."
    t4 = parse_command("Take the green bottle and give it to the JetArm.")
    assert t4.action == "pick_and_transfer"
    assert t4.object is not None
    assert t4.object.name == "bottle"
    assert t4.object.color == "green"
    assert t4.destination == "jetarm"
    print(f"[OK] 'Take the green bottle and give it to the JetArm.' -> action: '{t4.action}', object: '{t4.object.name}', color: '{t4.object.color}', dest: '{t4.destination}'")


def test_object_matching():
    print("\n--- 2. Testing Object Matcher with YOLO Detections ---")

    # Simulated YOLO + Color detections
    detections = [
        DetectedObject(
            name="bottle",
            confidence=0.94,
            color="red",
            bounding_box=BoundingBox(x1=120, y1=180, x2=260, y2=300),
            center=Point2D(x=190, y=240),
            coordinate_frame="IMAGE_COORDINATES_PIXELS",
        ),
        DetectedObject(
            name="bottle",
            confidence=0.91,
            color="green",
            bounding_box=BoundingBox(x1=320, y1=160, x2=440, y2=290),
            center=Point2D(x=380, y=225),
            coordinate_frame="IMAGE_COORDINATES_PIXELS",
        ),
        DetectedObject(
            name="cup",
            confidence=0.88,
            color="blue",
            bounding_box=BoundingBox(x1=480, y1=210, x2=580, y2=310),
            center=Point2D(x=530, y=260),
            coordinate_frame="IMAGE_COORDINATES_PIXELS",
        ),
        DetectedObject(
            name="mouse",
            confidence=0.95,
            color="black",
            bounding_box=BoundingBox(x1=60, y1=320, x2=150, y2=410),
            center=Point2D(x=105, y=365),
            coordinate_frame="IMAGE_COORDINATES_PIXELS",
        ),
    ]

    # Test Match 1: "Pick the red bottle." -> Should match red bottle
    t1 = parse_command("Pick the red bottle.")
    eval1 = object_matcher.evaluate_match(detections, t1)
    assert eval1.found
    assert not eval1.ambiguous
    assert eval1.target is not None
    assert eval1.target.name == "bottle"
    assert eval1.target.color == "red"
    assert eval1.target.center.x == 190 and eval1.target.center.y == 240
    assert eval1.target.coordinate_frame == "IMAGE_COORDINATES_PIXELS"
    print(f"[OK] Matched '{eval1.target.color} {eval1.target.name}' at image center ({eval1.target.center.x}, {eval1.target.center.y})")

    # Test Match 2: "Find the blue cup." -> Should match blue cup
    t2 = parse_command("Find the blue cup.")
    eval2 = object_matcher.evaluate_match(detections, t2)
    assert eval2.found
    assert eval2.target is not None
    assert eval2.target.name == "cup"
    assert eval2.target.color == "blue"
    assert eval2.target.center.x == 530 and eval2.target.center.y == 260
    print(f"[OK] Matched '{eval2.target.color} {eval2.target.name}' at image center ({eval2.target.center.x}, {eval2.target.center.y})")

    # Test Match 3: "Pick the mouse." -> Should match mouse (color unconstrained)
    t3 = parse_command("Pick the mouse.")
    eval3 = object_matcher.evaluate_match(detections, t3)
    assert eval3.found
    assert eval3.target is not None
    assert eval3.target.name == "mouse"
    assert eval3.target.center.x == 105 and eval3.target.center.y == 365
    print(f"[OK] Matched '{eval3.target.name}' at image center ({eval3.target.center.x}, {eval3.target.center.y})")

    # Test Match 4: Object NOT found: "Pick the yellow bottle."
    t4 = parse_command("Pick the yellow bottle.")
    eval4 = object_matcher.evaluate_match(detections, t4)
    assert not eval4.found
    assert eval4.target is None
    print(f"[OK] Missing object handled cleanly: found={eval4.found}, reason='{eval4.reason}'")

    # Test Match 5: Object class NOT present: "Locate the banana."
    t5 = parse_command("Locate the banana.")
    eval5 = object_matcher.evaluate_match(detections, t5)
    assert not eval5.found
    print(f"[OK] Non-existent class handled cleanly: found={eval5.found}, reason='{eval5.reason}'")

    # Test Match 6: Ambiguity handling: Multiple bottles when no color specified
    t6 = parse_command("Pick a bottle.")
    eval6 = object_matcher.evaluate_match(detections, t6)
    assert eval6.found
    assert eval6.ambiguous
    assert len(eval6.candidates) == 2
    print(f"[OK] Ambiguity handled cleanly: found={eval6.found}, ambiguous={eval6.ambiguous}, candidate count={len(eval6.candidates)}")


if __name__ == "__main__":
    test_command_parsing()
    test_object_matching()
    print("\n==================================================")
    print("  ALL COMMAND -> OBJECT MATCHING TESTS PASSED!    ")
    print("==================================================")
