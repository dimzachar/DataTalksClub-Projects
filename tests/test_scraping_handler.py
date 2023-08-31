class TestScrapingHandler:
    def setup_method(self):
        self.scraping_handler = ScrapingHandler(
            mock_url, mock_folder_path, mock_course, mock_year
        )

    def test_scrape_data(self):
        # Test if the function returns an integer (number of tables scraped)
        assert isinstance(self.scraping_handler.scrape_data(), int)