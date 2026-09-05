# Automated Job Search & ATS CV Generator

A modular Python/FastAPI backend designed to scrape multiple job sources, store offers in a local database, evaluate them via AI, and generate ATS-optimized custom PDF resumes.

## Features
- **Multi-source Scraper**: Modular architecture for platforms like Wellfound, We Work Remotely, and company career pages.
- **Database Tracking**: Persistent storage using SQLite and SQLModel to prevent duplicate applications.
- **AI-Driven Matching**: Analyzes job requirements against your core CV.
- **ATS-Optimized PDF Generator**: Renders clean, text-selectable PDF resumes without formatting blocks that break ATS parsers.
