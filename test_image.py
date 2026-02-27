from image_generator import create_quote_image

if __name__ == "__main__":
    try:
        img = create_quote_image(None, "Test Name", "This is a test quote.")
        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()
