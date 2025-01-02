
# Quest by Cycle's Badge Contest

Welcome to Quest by Cycle's Badge Contest, an innovative project designed to merge art, sustainability, and community engagement. This platform allows artists of all ages to contribute their creative talents by designing badges for the Quest by Cycle game, a gamified experience promoting cycling and environmental stewardship.

This project is proudly funded by a grant from the Oregon Cultural Trust, enabling us to support arts, heritage, and humanities initiatives in our community.

## Table of Contents

- Project Overview
- Application Details
    - Call for Artists
    - Call for Youth Artists
- Technical Features
- Directory Structure
- Setup Guide
    - Requirements
    - Installation
    - Database Setup
    - Running the Application
    - Production Deployment
- API Endpoints
- Development Workflow
- Acknowledgements
- License

## Project Overview

Quest by Cycle is a grassroots initiative designed to promote cycling, sustainability, and community participation. Players earn points by completing quests tied to these values, and badges serve as digital rewards to celebrate their achievements.

The purpose of this platform is to engage both professional and youth artists to create compelling badge designs that will inspire players to take part in sustainable activities. Through these creative contributions, we hope to connect the local art community with environmental advocacy.

This project is supported by the Oregon Cultural Trust, which plays a vital role in funding arts, heritage, and humanities projects across Oregon. To support their work, visit culturaltrust.org.

## Application Details

### Call for Artists

- **Eligibility**: Open to all artists, regardless of location or experience level.
- **Awards**: Ten winning artists will receive $200 each.
- **Guidelines for Submission**:
    - **Design Format**:
        - Non-AI designs.
        - Digital submissions (e.g., .SVG, .PNG, .JPEG) should be high resolution (300 DPI or higher).
        - Traditional media submissions must include high-quality photographs.
    - **Theme Requirements**: Badge designs should reflect the themes of cycling, sustainability, local culture, and community engagement.
    - **Limitations**: Artists may submit up to three designs.
- **Timeline**:
    - **Start Date**: Refer to the submission period on the website.
    - **Deadline**: See the timeline listed on the submission portal.

### Call for Youth Artists

- **Eligibility**: Open to artists aged 13–18.
- **Awards**: Seven youth artists will be awarded cycling accessories like lights, fenders, or pumps.
- **Guidelines for Submission**:
    - **Design Format**:
        - Same format and requirements as the general Call for Artists.
    - **Theme Requirements**: Similar to the general contest, badge designs should reflect themes of sustainability, community, and cycling.

## Technical Features

### Submission Portal

- **Custom Forms**: Dynamic forms for artist submissions, integrated with file upload capabilities.
- **Validation**: Both client-side (JavaScript) and server-side (Flask-WTF) validation for submission accuracy.
- **File Handling**: Submissions are securely stored in the server's file system under the static/submissions/ directory.

### Judge Panel

- **Secure Login**: Password-protected access for judges, with role-based permissions (Admin vs. Judge).
- **Ranking System**: Judges rank submissions, and results are calculated in real time.

### Badge Management

- **Admin Features**:
    - Create, edit, delete badges.
    - Upload badge details via CSV for bulk management.
- **Dynamic Display**: Badge details are dynamically displayed on the submission portal.

### API Integration

- **RESTful endpoints for fetching badge data and submissions**.
- **Example endpoints include**:
    - `/api/badges` – Retrieve all available badges.
    - `/api/artwork-detail/<id>` – Fetch details for specific submissions.

## Directory Structure

The project is structured for modularity and maintainability:

```
ArtSubmissionSite/
├── app/
│   ├── __init__.py              # App factory and configuration
│   ├── forms.py                 # Form definitions for submissions and admin actions
│   ├── models.py                # Database models
│   ├── routes.py                # Route handlers for web pages
│   ├── templates/               # HTML templates (Jinja2)
│   │   ├── admin.html
│   │   ├── index.html
│   │   ├── judges_ballot.html
│   │   ├── submission_success.html
│   │   └── ... (other pages)
│   ├── static/
│   │   ├── css/                 # CSS files
│   │   ├── js/                  # JavaScript files
│   │   ├── submissions/         # Uploaded artwork
│   │   ├── videos/              # Embedded videos
│   │   └── favicon.ico          # App icon
│   └── __pycache__/             # Compiled Python files
├── config.toml                  # Application configuration
├── run.py                       # Entry point for running the app
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation (this file)
```

## Setup Guide

### Requirements

- Python: 3.11 or later.
- Flask: 3.0.3.
- PostgreSQL: Database for managing submissions and judges.

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/username/ArtSubmissionSite.git
   cd ArtSubmissionSite
   ```

2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate  # For Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Database Setup

1. Create a PostgreSQL database:
   ```
   CREATE DATABASE artcontest;
   ```

2. Update config.toml with your database credentials:
   ```
   SQLALCHEMY_DATABASE_URI = "postgresql://username:password@localhost/artcontest"
   ```

3. Apply database migrations:
   ```
   flask db upgrade
   ```

### Running the Application

1. Start the Flask development server:
   ```
   python run.py
   ```

2. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

### Production Deployment

1. Use Gunicorn as a WSGI server for production:
   - Install Gunicorn:
     ```
     pip install gunicorn
     ```

   - Run the app using Gunicorn:
     ```
     gunicorn -w 4 -b 0.0.0.0:5000 app:app
     ```

   - (Optional) Set up a reverse proxy using Nginx for SSL termination and load balancing.

## API Endpoints

### Public Endpoints

- Fetch all badges:
  - GET /api/badges

- Fetch carousel images:
  - GET /carousel-images

### Admin Endpoints

- Manage Badges:
  - POST /admin/badges
    - Add, edit, or delete badge entries.

- Clear Judge Votes:
  - POST /admin/clear_votes

## Development Workflow

1. Add New Features:
   - Update routes.py for new pages.
   - Create new templates in templates/.

2. Run Tests:
   - Write test cases for views and models.
   - Use pytest:
     ```
     pytest
     ```

3. Commit Changes:
   - Follow semantic commit messages:
     ```
     feat: Add youth artist submission form
     ```

4. Deploy Updates:
   - Push changes to the production branch.
   - Restart the Gunicorn service.

## Acknowledgements

- Oregon Cultural Trust: For funding and support.
- Contributors: Thank you to everyone who helped build this project.

## License

This project is licensed under the MIT License. See LICENSE for details.
