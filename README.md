# SC Atlas Tracker

An auto-updating dashboard, refreshed daily by a scheduled Claude task.

## Status

Scaffold only. This repo is set up and the daily update pipeline is being wired up. Real content coming soon.

## Structure

The dashboard page is index.html, a static page with no build step. The data folder holds daily data snapshots written by the scheduled update job. CHANGELOG.md gets one new line per day, appended automatically on each update.

## How it updates

A Claude scheduled task runs once a day, regenerates data/latest.json and index.html, and pushes the change to this repo.
