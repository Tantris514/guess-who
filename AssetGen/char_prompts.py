"""Prompt fragments shared by the character edits."""
POSE = ("Keep exactly the same pose: shoulders at the same height and width, arms straight and angled down away from the body "
        "at the same wide angle, same arm thickness, wrists and open hands at exactly the same place, clearly separated from the "
        "hips and the clothes, legs slightly apart with a clear gap between them exactly like the mannequin. Same body "
        "proportions, same height, same scale and same position in the frame, full body from head to toe, orthographic. "
        "Plain uniform light grey studio background, soft even lighting, photorealistic, no props, nothing lying on the floor.")
BACK = ("Image 1 shows a mannequin seen from behind. Dress it as exactly the same person and outfit as in image 2, now seen "
        "from directly behind: {desc} Keep exactly the pose of image 1: same arm thickness, arms straight and angled away "
        "from the body at the same wide angle, hands at exactly the same place, clearly separated from the hips and the "
        "clothes, legs slightly apart with a clear gap between them, same body proportions, same scale and same position in "
        "the frame, full body from head to toe, back view, orthographic. Plain uniform light grey studio background, soft even "
        "lighting, photorealistic, no props, nothing lying on the floor.")
SIDE = ("Image 1 shows a mannequin seen exactly from its side, in profile, facing left. Dress it as exactly the same person and "
        "outfit as in image 2, now seen in profile from the side, facing left: {desc} Keep exactly the pose and profile of "
        "image 1: same posture, arms hanging at the same place beside the body, same body proportions, same scale and same "
        "position in the frame, full body from head to toe, side view, orthographic. Plain uniform light grey studio "
        "background, soft even lighting, photorealistic, no props, nothing lying on the floor.")
