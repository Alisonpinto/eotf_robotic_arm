import asyncio
from robots.manager import robot_manager
from robots.models import JointAngles, Pose3D
from ai.interpreter import ai_interpreter, parse_command
from tasks.task_manager import task_manager
from vision.processor import vision_processor

async def main():
    print("==================================================")
    print("  RUNNING ROBOT-AI BACKEND VERIFICATION SUITE")
    print("==================================================")

    # 1. Verify Robots Registry & Telemetry
    robots = robot_manager.list_robots()
    assert len(robots) == 2, f"Expected 2 robots, found {len(robots)}"
    diy = robot_manager.get_robot("diy_arm")
    jet = robot_manager.get_robot("jetarm")
    assert diy is not None and jet is not None
    print(f"[OK] Robots registered: {diy.get_name()} ({diy.get_id()}), {jet.get_name()} ({jet.get_id()})")

    # 2. Verify Dynamic Natural-Language Command Parser (User Examples)
    print("\n--- Verifying Dynamic Natural-Language Command Parser ---")

    # Example 1: "Pick the red bottle."
    task1 = parse_command("Pick the red bottle.")
    print(f"[Test 1] 'Pick the red bottle.' ->")
    print(f"   action: {task1.action}")
    print(f"   object.name: {task1.object.name if task1.object else None}")
    print(f"   object.attributes: {task1.object.attributes.model_dump() if task1.object else None}")
    assert task1.action == "pick"
    assert task1.object is not None and task1.object.name == "bottle"
    assert task1.object.attributes.color == "red"
    print("[OK] Test 1 Passed!")

    # Example 2: "Pick the blue cup and give it to the JetArm."
    task2 = parse_command("Pick the blue cup and give it to the JetArm.")
    print(f"\n[Test 2] 'Pick the blue cup and give it to the JetArm.' ->")
    print(f"   action: {task2.action}")
    print(f"   object: {task2.object.name if task2.object else None}, color: {task2.object.attributes.color if task2.object else None}")
    print(f"   source: {task2.source}, destination: {task2.destination}")
    assert task2.action == "pick_and_transfer"
    assert task2.object is not None and task2.object.name == "cup"
    assert task2.object.attributes.color == "blue"
    assert task2.destination == "jetarm"
    assert task2.source == "diy_arm"
    print("[OK] Test 2 Passed!")

    # Example 3: "Find the box and move it to the right."
    task3 = parse_command("Find the box and move it to the right.")
    print(f"\n[Test 3] 'Find the box and move it to the right.' ->")
    print(f"   action: {task3.action}")
    print(f"   object: {task3.object.name if task3.object else None}")
    print(f"   destination: {task3.destination}")
    assert task3.action in ("find_and_move", "move", "find")
    assert task3.object is not None and task3.object.name == "box"
    assert task3.destination == "right"
    print("[OK] Test 3 Passed!")

    # Example 4: Novel arbitrary command: "Locate the small yellow canister and pass it to the DIY arm."
    task4 = parse_command("Locate the small yellow canister and pass it to the DIY arm.")
    print(f"\n[Test 4] Novel Command: 'Locate the small yellow canister and pass it to the DIY arm.' ->")
    print(f"   action: {task4.action}")
    print(f"   object: {task4.object.name if task4.object else None}, size: {task4.object.attributes.size}, color: {task4.object.attributes.color}")
    print(f"   source: {task4.source}, destination: {task4.destination}")
    assert task4.action == "pick_and_transfer"
    assert task4.object is not None and task4.object.name == "canister"
    assert task4.object.attributes.color == "yellow"
    assert task4.object.attributes.size == "small"
    assert task4.destination == "diy_arm"
    assert task4.source == "jetarm"
    print("[OK] Test 4 Passed!")

    # 3. Verify Full Interpretation & Task Execution Pipeline
    cmd = "Pick the red bottle and give it to the JetArm."
    plan = await ai_interpreter.interpret(cmd)
    assert plan.structured_task is not None
    assert plan.structured_task.action == "pick_and_transfer"
    print(f"\n[OK] Interpretation Pipeline Succeeded: intent={plan.intent}, actions={len(plan.actions)}")

    task_rec = task_manager.create_task(plan)
    assert task_rec.structured_task is not None
    assert task_rec.structured_task.object.name == "bottle"
    started = task_manager.start_task(task_rec.task_id)
    assert started is True
    print(f"[OK] Task launched with structured task representation: {task_rec.task_id}")

    # Wait briefly for steps
    await asyncio.sleep(0.8)
    curr_task = task_manager.get_task(task_rec.task_id)
    print(f"[OK] Task progress: {curr_task.progress_pct}%, step: {curr_task.current_step_desc}")

    # 4. Verify Computer Vision Subsystem (Detector & Matcher)
    print("\n--- Verifying Computer Vision Subsystem ---")
    from vision.camera import camera_source
    from vision.detector import vision_detector
    from vision.object_matcher import object_matcher, ObjectMatchQuery

    # Generate sample workbench image
    sample_img = camera_source.generate_sample_workbench_image()
    assert sample_img is not None and sample_img.shape == (480, 640, 3)
    print(f"[OK] CameraSource generated test workbench image: {sample_img.shape}")

    # Run OpenCV Detector
    detected = vision_detector.detect(sample_img)
    assert len(detected) >= 3, f"Expected at least 3 detected objects, got {len(detected)}"
    print(f"[OK] VisionDetector identified {len(detected)} objects:")
    for obj in detected:
        print(f"   • {obj.name} (color: {obj.color}, conf: {obj.confidence})")
        print(f"     bbox: [x1:{obj.bounding_box.x1}, y1:{obj.bounding_box.y1}, x2:{obj.bounding_box.x2}, y2:{obj.bounding_box.y2}]")
        print(f"     center: [x:{obj.center.x}, y:{obj.center.y}] in {obj.coordinate_frame}")
        assert obj.bounding_box.x2 > obj.bounding_box.x1
        assert obj.bounding_box.y2 > obj.bounding_box.y1

    # Verify Object Matcher with Task (e.g. "red bottle")
    match_query = ObjectMatchQuery(name="bottle", color="red")
    match_result = object_matcher.match(detected, match_query)
    assert match_result.matched is True
    assert match_result.matched_object.name == "bottle"
    assert match_result.matched_object.color == "red"
    assert match_result.image_coordinates is not None
    assert "center" in match_result.image_coordinates
    assert match_result.coordinate_frame == "IMAGE_COORDINATES_PIXELS"
    assert "PENDING_CALIBRATION" in match_result.robot_coordinates_status
    print(f"[OK] ObjectMatcher successfully matched 'red bottle':")
    print(f"     Match score: {match_result.match_score}")
    print(f"     Image Coords: center={match_result.image_coordinates['center']}")
    print(f"     Robot Coords Status: {match_result.robot_coordinates_status}")

    # Verify Object Matcher with "blue cup"
    match_cup = object_matcher.match(detected, ObjectMatchQuery(name="cup", color="blue"))
    assert match_cup.matched is True
    assert match_cup.matched_object.name == "cup"
    print(f"[OK] ObjectMatcher successfully matched 'blue cup' (center={match_cup.image_coordinates['center']})")

    print("\n==================================================")
    print("  ALL BACKEND, PARSER & VISION TESTS PASSED!       ")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
