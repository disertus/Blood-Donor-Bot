# Blood-Donor-Bot

### Intro
The creation of **@donor_notify_bot** was inspired by lack of certain types of donor blood in blood banks in Ukraine.
Bot's notification system should raise people's awareness about the existing shortages.

#### What this telegram bot does?:
- Checks the availability of different blood types at the municipal blood bank
- Collects the data about users' blood type
- Schedules the donations using the info about users' last donation
- Informs the users when there is a lack of blood at the blood bank if their blood type and scheduled date match, reschedules the notification if not
- Stores chronological data about the availability of specific blood types into MySQL Server instance (makes it possible to further analyze the data)

![Donor notify bot](https://i.ibb.co/VvX1k57/Screenshot-from-2020-06-15-11-23-37.png)

Check the availability of all blood types:

![Check blood availability](https://i.ibb.co/sR1qYzR/Screenshot-from-2020-06-15-11-25-31.png)

Find the geo-location of the Blood Bank on the map:

![Blood bank location](https://i.ibb.co/DVprHfV/Screenshot-from-2020-06-16-11-29-56.png)

This bot could become scalable to the different blood banks in other cities. 

Check it out in action at @donor_notify_bot.
