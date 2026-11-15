# Roles and projects

Access to project data needs two permissions:

- a **role group** for what a user may do with each kind of record: "Viewer", "Researcher" or "Principal Investigator", plus optional domain groups such as "Luminescence" or "Pollen";
- **membership in the project** for whose data.

Assign every staff user a role group. Without one, a user can log in but sees no project data. `manage.py deploy` lists such users before it asks for confirmation.

The role groups are created after every `migrate`. To rebuild them, for example after adding a model, run `python manage.py create_permission_groups --reset`.

Project members are managed on the project's admin page. Saving the project grants each member view, add and change permission on the project's data and removes them from former members; delete permission is granted separately. Code that adds members outside the admin calls `prototype.access.sync_member_permissions(project)` for the same effect.

Literature locations (`data_source="literature"`) belong to no project and are visible to every authenticated user.
