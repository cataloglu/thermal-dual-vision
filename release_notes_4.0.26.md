## Release 4.0.26

- Fixed person class filtering robustness: COCO `class_id=0` is now always accepted as person even if `names` metadata is wrong/misaligned.
- Prevents OpenVINO/export `names_map` issues from filtering out real person boxes and producing `DETECT_PIPELINE raw=0`.

