class Article:

    def __init__(self, url, title, story_text, autor="unknown", clearfix="unknown",
                 dateTime="unknown", dateAkt="unknown", photos_videos=None):
        self.url = url
        self.title = title
        self.clearfix = clearfix
        self.dateTime = dateTime
        self.dateAkt = dateAkt
        self.story_text = story_text
        self.autor = autor
        self.photos_videos = photos_videos
