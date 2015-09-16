from mock import patch

from sentry.models import (
    GroupTagKey, GroupTagValue, Organization, OrganizationStatus, TagKey,
    TagValue, Team, TeamStatus
)
from sentry.tasks.deletion import (
    delete_organization, delete_tag_key, delete_team
)
from sentry.testutils import TestCase


class DeleteOrganizationTest(TestCase):
    def test_simple(self):
        org = self.create_organization(
            name='test',
            status=OrganizationStatus.PENDING_DELETION,
        )
        team1 = self.create_team(organization=org, name='test1')
        team2 = self.create_team(organization=org, name='test2')

        with self.tasks():
            delete_organization(object_id=org.id)

        assert not Organization.objects.filter(id=org.id).exists()


class DeleteTeamTest(TestCase):
    def test_simple(self):
        team = self.create_team(
            name='test',
            status=TeamStatus.PENDING_DELETION,
        )
        project1 = self.create_project(team=team, name='test1')
        project2 = self.create_project(team=team, name='test2')

        with self.tasks():
            delete_team(object_id=team.id)

        assert not Team.objects.filter(id=team.id).exists()


class DeleteTagKeyTest(TestCase):
    @patch.object(delete_tag_key, 'delay')
    def test_simple(self, delete_tag_key_delay):
        team = self.create_team(name='test', slug='test')
        project = self.create_project(team=team, name='test1', slug='test1')
        group = self.create_group(project=project)
        tk = TagKey.objects.create(key='foo', project=project)
        TagValue.objects.create(key='foo', value='bar', project=project)
        GroupTagKey.objects.create(key='foo', group=group, project=project)
        GroupTagValue.objects.create(key='foo', value='bar', group=group, project=project)

        project2 = self.create_project(team=team, name='test2')
        group2 = self.create_group(project=project2)
        tk2 = TagKey.objects.create(key='foo', project=project2)
        gtk2 = GroupTagKey.objects.create(key='foo', group=group2, project=project2)
        gtv2 = GroupTagValue.objects.create(key='foo', value='bar', group=group2, project=project2)

        with self.tasks():
            delete_tag_key(object_id=tk.id)

            assert not GroupTagValue.objects.filter(key=tk.key, project=project).exists()

            delete_tag_key_delay.assert_called_once_with(object_id=tk.id, countdown=15)

            delete_tag_key_delay.reset_mock()

            delete_tag_key(object_id=tk.id)

            assert not GroupTagKey.objects.filter(key=tk.key, project=project).exists()

            delete_tag_key_delay.assert_called_once_with(object_id=tk.id, countdown=15)

            delete_tag_key_delay.reset_mock()

            delete_tag_key(object_id=tk.id)

            assert not TagValue.objects.filter(key=tk.key, project=project).exists()

            delete_tag_key_delay.assert_called_once_with(object_id=tk.id, countdown=15)

            delete_tag_key_delay.reset_mock()

            delete_tag_key(object_id=tk.id)

            assert not delete_tag_key_delay.called

            assert not TagKey.objects.filter(id=tk.id).exists()

        assert TagKey.objects.filter(id=tk2.id).exists()
        assert GroupTagKey.objects.filter(id=gtk2.id).exists()
        assert GroupTagValue.objects.filter(id=gtv2.id).exists()
