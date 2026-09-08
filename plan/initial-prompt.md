Use the pdfs in ./data to furnish a csv with the column structure below by taking the info from the Partners / 'Who are you working with' section to coerce it into the columns in ./exports/example.csv

Ignore the first table in the pdf that displays in the info in an actual column as a birds eye view with crucial stuff tailing off into elipses. instead identif the full partners list that comes after with individiual fields

PDF field name | CSV Col | CSV Col Name | Notes
Name: | B | Name | Name of the individual or organisation in question
Main contact (if organisation): | C | Rep (if org) | Name of main contact or representative at organisation, if an organisation, if not, leave blank
Role in project: | E | Role/Bio | Used as a bio for key project partners but also meant to describe their contribution
Email address: | D | Email | Email address

Re: other columns, as per example.csv
- Col A in the CSV should contain the grant bid project name, which is found at the top of every page of the PDF, justified left, by the word 'Project:', it should be identical for every entry from the same pdf, and if it's a long project name, e.g. more than 10 words, cut it down to 8 max
- When capturing the project name, make sure you don't confuse the in line justified right text called 'NLPG-########...' with the unique reference number the funder use, don't fold that in
- Cols F, G and H are to be filled by my assistant after
- 'The Confirmed or expected:' field in the pdfs is irrelevant

Deliverables:
- A standardised method that is foolproof, can use python potentially or whatever other tools you need/prefer
- A csv per pdf in ./exports with a name following the format YYYY-MM-{applicant-first-name}-{applicant-surname}-{first-3-words-of-project-name}
- Where the year and month are the starting year and month on page 4 of each pdf, next to the field 'Project start date:' but in reverse date order, not inc. day
- Where applicant name is taken from page 2 of each pdf next to field 'Applicant name:', if org then the first two words of the org name will suffice, if only one name then skip the {surname} component
- Check the first few entries you create against the contents of the pdf by verifying in more manual labour intensive ways, to perfect your python script
- Make development notes in ./plan to document your progress for yourself and for me, with nomenclature ##_{title}.md

Prompt taken from ./plan/initial-prompt.md
