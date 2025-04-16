import os

def cleanup_data():
    print("=== Starting Cleanup ===")
    
    # 1. Delete SQLite database
    try:
        if os.path.exists("syna.db"):
            os.remove("syna.db")
            print("✓ Database deleted successfully")
    except Exception as e:
        print(f"Error deleting database: {e}")

    # 2. Delete match cache
    try:
        if os.path.exists("matches_cache.json"):
            os.remove("matches_cache.json")
            print("✓ Match cache deleted successfully")
    except Exception as e:
        print(f"Error deleting match cache: {e}")

    # 3. Delete feedback file
    try:
        if os.path.exists("feedback.txt"):
            os.remove("feedback.txt")
            print("✓ Feedback file deleted successfully")
    except Exception as e:
        print(f"Error deleting feedback file: {e}")

    print("\n=== Cleanup Complete ===")
    print("You can now restart the application and create new test accounts!")

if __name__ == "__main__":
    cleanup_data()