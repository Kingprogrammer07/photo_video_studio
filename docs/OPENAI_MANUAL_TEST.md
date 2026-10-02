# OpenAI Manual Test Checklist

Last updated: 2026-10-02

Use this checklist only with a real OpenAI API key and non-sensitive test photos. Original photos must remain unchanged.

## Setup

1. Run `python app.py`.
2. Open `Sozlamalar`.
3. Paste the OpenAI API key and click `Saqlash`.
4. Click `Tekshirish` and confirm the status says the key works.
5. Confirm `%APPDATA%\PhotoVideoStudio\settings.json` does not contain the API key.

## Consent

1. Leave the AI consent switch off.
2. Add one test photo in `Slideshow`.
3. Open `AI Rasm Studio`.
4. Click `OpenAI bilan tanlangan rasm`.
5. Confirm the app asks for consent before sending the photo online.
6. Decline once and confirm no cache file is created.
7. Try again, accept consent, and confirm the setting is saved.

## Selected Photo Enhance

1. Choose one photo.
2. Set a visible AI/pro adjustment, for example higher saturation and sharpness.
3. Run `OpenAI bilan tanlangan rasm`.
4. Confirm the photo row shows `[AI]`.
5. Confirm the draggable `Oldin/Keyin` divider displays a visible difference.
6. Confirm the enhanced file appears under `%APPDATA%\PhotoVideoStudio\cache\ai\`.
7. Confirm the original photo bytes and modified time did not change.

## Render With Enhanced Photo

1. Select a starter template in `Fonlar/Shablonlar`.
2. Render a short preview.
3. Confirm the rendered video uses the enhanced photo and the selected background.
4. Click `Bekor qilish` during another preview render and confirm the app returns to a ready state.

## Error Cases

1. Delete the saved key, then run OpenAI enhance and confirm the app asks for a key.
2. Use a wrong key and confirm the UI shows a readable error.
3. Disable internet and confirm the app fails without changing the original photo.
4. Confirm local enhancement still works without internet.
