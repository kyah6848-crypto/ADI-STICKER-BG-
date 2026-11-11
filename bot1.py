import os
import cv2
import numpy as np
from PIL import Image
from rembg import remove
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "9011301414:AAGD34o3if-GZuHRaqLVYXPxkCqdzC9BzdY"

STATE_WAITING_PHOTO = "WAITING_PHOTO"
STATE_WAITING_VIDEO = "WAITING_VIDEO"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "Remove Photo Background and Create Sticker",
                callback_data="btn_photo",
            )
        ],
        [
            InlineKeyboardButton(
                "Remove Video Background and Create Sticker",
                callback_data="btn_video",
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please select an option below:", reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_photo":
        context.user_data["state"] = STATE_WAITING_PHOTO
        await query.edit_message_text(
            text="Please send the photo you want to convert into a sticker."
        )
    elif query.data == "btn_video":
        context.user_data["state"] = STATE_WAITING_VIDEO
        await query.edit_message_text(
            text="Please send the video you want to convert into an animated sticker."
        )

def make_square(img: Image.Image) -> Image.Image:
    width, height = img.size
    max_dim = max(width, height)
    square_img = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
    offset = ((max_dim - width) // 2, (max_dim - height) // 2)
    square_img.paste(img, offset)
    return square_img.resize((512, 512), Image.Resampling.LANCZOS)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != STATE_WAITING_PHOTO:
        await update.message.reply_text("Please use /start to select an option first.")
        return

    status_msg = await update.message.reply_text("Processing photo...")
    input_path = f"input_{update.message.message_id}.png"
    output_path = f"sticker_{update.message.message_id}.webp"

    try:
        photo_file = await update.message.photo[-1].get_file()
        await photo_file.download_to_drive(input_path)

        input_image = Image.open(input_path)
        output_image = remove(input_image)
        square_sticker = make_square(output_image)
        square_sticker.save(output_path, "WEBP", format="WEBP")

        with open(output_path, "rb") as sticker_file:
            await update.message.reply_sticker(sticker=sticker_file)

        context.user_data["state"] = None
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")
    finally:
        await status_msg.delete()
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != STATE_WAITING_VIDEO:
        await update.message.reply_text("Please use /start to select an option first.")
        return

    status_msg = await update.message.reply_text("Processing video frame-by-frame...")
    input_path = f"input_{update.message.message_id}.mp4"
    output_path = f"sticker_{update.message.message_id}.webm"

    try:
        video_file = await update.message.video.get_file()
        await video_file.download_to_drive(input_path)

        cap = cv2.VideoCapture(input_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        fourcc = cv2.VideoWriter_fourcc(*"VP90")
        out = cv2.VideoWriter(output_path, fourcc, fps, (512, 512), True)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)
            nobg_img = remove(pil_img)
            square_img = make_square(nobg_img)

            bgra_frame = cv2.cvtColor(np.array(square_img), cv2.COLOR_RGBA2BGRA)
            out.write(bgra_frame)

        cap.release()
        out.release()

        with open(output_path, "rb") as sticker_file:
            await update.message.reply_sticker(sticker=sticker_file)

        context.user_data["state"] = None
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")
    finally:
        await status_msg.delete()
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    app.run_polling()

if __name__ == "__main__":
    main()
