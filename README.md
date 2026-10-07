# Familienfelsen

Familienfelsen is a simple web application for discovering and contributing family-friendly climbing crags.

The project focuses on one core idea: families need reliable, easy-to-find climbing information that helps them decide quickly whether a location is suitable for their children.

This project is open source. Feature ideas, feedback, and bug reports are welcome via GitHub Issues.
- [Development Plan](https://github.com/users/ripertio/projects/2/views/1)
- [Create Feature Request or Bug Report](https://github.com/ripertio/felsen-mit-kids/issues/new/choose)

## Vision

Families should be able to answer: “Where can we go climbing with our kids, and is this place suitable for our distinct family needs?”

## Goals

- make suitable crags easy to discover
- provide clear family-relevant information
- keep moderation simple and practical
- mobile-first and easy to use in the field

## Features

### Public discovery
- search crags
- filter by area and family suitability
- browse public crag listings
- view dedicated detail pages

### Crag information
- [Crag Information](Crag%20Details.md) 

### Community contributions
Authenticated users can:
- create crag entries
- edit their own submissions
- upload photos
- submit content for review

### Moderation and administration
Admins can:
- review pending submissions
- publish or reject content
- correct information
- manage areas, guidebooks, and users
- remove inappropriate content

### Maintenance-friendly architecture
- Docker Compose-based development environment
- PostgreSQL for persistence
- simple deployment model suitable for server migration and backup/restore

---

## Core principles

- simple server-rendered architecture
- mobile-first UX
- PostgreSQL as the system of record
- community-contributed content
- Docker-based local development and operations
- maintainability over complexity
- recovery and portability over vendor lock-in  


##  Technical overview

- Python / Django
- Django Templates
- PostgreSQL
- Docker Compose
- Caddy or Traefik
- Docker volumes for persistent data and media


## Summary

Familienfelsen is a focused application for family-friendly climbing discovery and contribution. It brings together a simple public experience, a lightweight community workflow, and a maintainable architecture suited to long-term operation.