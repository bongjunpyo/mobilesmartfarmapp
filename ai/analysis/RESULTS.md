# 오분류 분석 결과 (자동 생성)

- 모델: `model/best_crop_model.onnx` (onnxruntime CPU)
- 대상: `test_images/` 라벨 이미지 33장
- 전체 정확도: **23/33 (69.7%)**

## 클래스별 지표

| 클래스 | support | 예측 건수 | precision | recall | F1 |
|---|---|---|---|---|---|
| Potato___Early_blight | 5 | 1 | 1.00 | 0.20 | 0.33 |
| Potato___healthy | 2 | 2 | 1.00 | 1.00 | 1.00 |
| Tomato___Bacterial_spot | 0 | 2 | 0.00 | 0.00 | 0.00 |
| Tomato___Early_blight | 6 | 3 | 1.00 | 0.50 | 0.67 |
| Tomato___Tomato_Yellow_Leaf_Curl_Virus | 6 | 6 | 1.00 | 1.00 | 1.00 |
| Tomato___Tomato_mosaic_virus | 0 | 1 | 0.00 | 0.00 | 0.00 |
| Tomato___healthy | 4 | 3 | 1.00 | 0.75 | 0.86 |
| Pepper,_bell___Bacterial_spot | 0 | 1 | 0.00 | 0.00 | 0.00 |
| Pepper,_bell___healthy | 0 | 2 | 0.00 | 0.00 | 0.00 |
| Apple___Apple_scab | 3 | 1 | 1.00 | 0.33 | 0.50 |
| Apple___Cedar_apple_rust | 4 | 5 | 0.80 | 1.00 | 0.89 |
| Apple___healthy | 0 | 3 | 0.00 | 0.00 | 0.00 |
| Corn_(maize)___Common_rust_ | 3 | 3 | 1.00 | 1.00 | 1.00 |

## 오분류 사례

| 파일 | 정답 | 예측 | 예측 확신도 | 정답 확률 |
|---|---|---|---|---|
| AppleScab1.JPG | Apple___Apple_scab | Apple___Cedar_apple_rust | 0.84 | 0.00 |
| AppleScab3.JPG | Apple___Apple_scab | Apple___healthy | 0.49 | 0.39 |
| PotatoEarlyBlight1.JPG | Potato___Early_blight | Pepper,_bell___healthy | 0.60 | 0.04 |
| PotatoEarlyBlight3.JPG | Potato___Early_blight | Apple___healthy | 0.77 | 0.00 |
| PotatoEarlyBlight4.JPG | Potato___Early_blight | Pepper,_bell___Bacterial_spot | 0.91 | 0.00 |
| PotatoEarlyBlight5.JPG | Potato___Early_blight | Pepper,_bell___healthy | 0.61 | 0.01 |
| TomatoEarlyBlight1.JPG | Tomato___Early_blight | Tomato___Bacterial_spot | 0.32 | 0.17 |
| TomatoEarlyBlight4.JPG | Tomato___Early_blight | Tomato___Tomato_mosaic_virus | 0.71 | 0.02 |
| TomatoEarlyBlight6.JPG | Tomato___Early_blight | Tomato___Bacterial_spot | 0.90 | 0.07 |
| TomatoHealthy1.JPG | Tomato___healthy | Apple___healthy | 0.60 | 0.09 |

## 전체 예측 로그

| 파일 | 정답 | 예측 | 확신도 | 정오 |
|---|---|---|---|---|
| AppleCedarRust1.JPG | Apple___Cedar_apple_rust | Apple___Cedar_apple_rust | 0.98 | O |
| AppleCedarRust2.JPG | Apple___Cedar_apple_rust | Apple___Cedar_apple_rust | 1.00 | O |
| AppleCedarRust3.JPG | Apple___Cedar_apple_rust | Apple___Cedar_apple_rust | 1.00 | O |
| AppleCedarRust4.JPG | Apple___Cedar_apple_rust | Apple___Cedar_apple_rust | 1.00 | O |
| AppleScab1.JPG | Apple___Apple_scab | Apple___Cedar_apple_rust | 0.84 | X |
| AppleScab2.JPG | Apple___Apple_scab | Apple___Apple_scab | 0.82 | O |
| AppleScab3.JPG | Apple___Apple_scab | Apple___healthy | 0.49 | X |
| CornCommonRust1.JPG | Corn_(maize)___Common_rust_ | Corn_(maize)___Common_rust_ | 0.92 | O |
| CornCommonRust2.JPG | Corn_(maize)___Common_rust_ | Corn_(maize)___Common_rust_ | 0.92 | O |
| CornCommonRust3.JPG | Corn_(maize)___Common_rust_ | Corn_(maize)___Common_rust_ | 0.94 | O |
| PotatoEarlyBlight1.JPG | Potato___Early_blight | Pepper,_bell___healthy | 0.60 | X |
| PotatoEarlyBlight2.JPG | Potato___Early_blight | Potato___Early_blight | 0.44 | O |
| PotatoEarlyBlight3.JPG | Potato___Early_blight | Apple___healthy | 0.77 | X |
| PotatoEarlyBlight4.JPG | Potato___Early_blight | Pepper,_bell___Bacterial_spot | 0.91 | X |
| PotatoEarlyBlight5.JPG | Potato___Early_blight | Pepper,_bell___healthy | 0.61 | X |
| PotatoHealthy1.JPG | Potato___healthy | Potato___healthy | 0.98 | O |
| PotatoHealthy2.JPG | Potato___healthy | Potato___healthy | 0.99 | O |
| TomatoEarlyBlight1.JPG | Tomato___Early_blight | Tomato___Bacterial_spot | 0.32 | X |
| TomatoEarlyBlight2.JPG | Tomato___Early_blight | Tomato___Early_blight | 0.80 | O |
| TomatoEarlyBlight3.JPG | Tomato___Early_blight | Tomato___Early_blight | 0.38 | O |
| TomatoEarlyBlight4.JPG | Tomato___Early_blight | Tomato___Tomato_mosaic_virus | 0.71 | X |
| TomatoEarlyBlight5.JPG | Tomato___Early_blight | Tomato___Early_blight | 0.95 | O |
| TomatoEarlyBlight6.JPG | Tomato___Early_blight | Tomato___Bacterial_spot | 0.90 | X |
| TomatoHealthy1.JPG | Tomato___healthy | Apple___healthy | 0.60 | X |
| TomatoHealthy2.JPG | Tomato___healthy | Tomato___healthy | 0.85 | O |
| TomatoHealthy3.JPG | Tomato___healthy | Tomato___healthy | 0.53 | O |
| TomatoHealthy4.JPG | Tomato___healthy | Tomato___healthy | 0.70 | O |
| TomatoYellowCurlVirus1.JPG | Tomato___Tomato_Yellow_Leaf_Curl_Virus | Tomato___Tomato_Yellow_Leaf_Curl_Virus | 0.99 | O |
| TomatoYellowCurlVirus2.JPG | Tomato___Tomato_Yellow_Leaf_Curl_Virus | Tomato___Tomato_Yellow_Leaf_Curl_Virus | 1.00 | O |
| TomatoYellowCurlVirus3.JPG | Tomato___Tomato_Yellow_Leaf_Curl_Virus | Tomato___Tomato_Yellow_Leaf_Curl_Virus | 1.00 | O |
| TomatoYellowCurlVirus4.JPG | Tomato___Tomato_Yellow_Leaf_Curl_Virus | Tomato___Tomato_Yellow_Leaf_Curl_Virus | 0.97 | O |
| TomatoYellowCurlVirus5.JPG | Tomato___Tomato_Yellow_Leaf_Curl_Virus | Tomato___Tomato_Yellow_Leaf_Curl_Virus | 0.88 | O |
| TomatoYellowCurlVirus6.JPG | Tomato___Tomato_Yellow_Leaf_Curl_Virus | Tomato___Tomato_Yellow_Leaf_Curl_Virus | 1.00 | O |
