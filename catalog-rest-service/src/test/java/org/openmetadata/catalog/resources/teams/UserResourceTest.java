/*
 *  Copyright 2021 Collate
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *  http://www.apache.org/licenses/LICENSE-2.0
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

package org.openmetadata.catalog.resources.teams;

import static java.util.List.of;
import static javax.ws.rs.core.Response.Status.BAD_REQUEST;
import static javax.ws.rs.core.Response.Status.CREATED;
import static javax.ws.rs.core.Response.Status.FORBIDDEN;
import static javax.ws.rs.core.Response.Status.NOT_FOUND;
import static javax.ws.rs.core.Response.Status.OK;
import static javax.ws.rs.core.Response.Status.UNAUTHORIZED;
import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.openmetadata.catalog.exception.CatalogExceptionMessage.entityNotFound;
import static org.openmetadata.catalog.exception.CatalogExceptionMessage.notAdmin;
import static org.openmetadata.catalog.exception.CatalogExceptionMessage.permissionNotAllowed;
import static org.openmetadata.catalog.security.SecurityUtil.authHeaders;
import static org.openmetadata.catalog.util.TestUtils.ADMIN_AUTH_HEADERS;
import static org.openmetadata.catalog.util.TestUtils.TEST_AUTH_HEADERS;
import static org.openmetadata.catalog.util.TestUtils.TEST_USER_NAME;
import static org.openmetadata.catalog.util.TestUtils.UpdateType.MINOR_UPDATE;
import static org.openmetadata.catalog.util.TestUtils.assertDeleted;
import static org.openmetadata.catalog.util.TestUtils.assertListNotNull;
import static org.openmetadata.catalog.util.TestUtils.assertListNull;
import static org.openmetadata.catalog.util.TestUtils.assertResponse;
import static org.openmetadata.catalog.util.TestUtils.assertResponseContains;
import static org.openmetadata.catalog.util.TestUtils.validateAlphabeticalOrdering;
import static org.openmetadata.common.utils.CommonUtil.listOrEmpty;
import static org.openmetadata.common.utils.CommonUtil.nullOrEmpty;

import com.auth0.jwt.JWT;
import com.auth0.jwt.exceptions.JWTDecodeException;
import com.auth0.jwt.interfaces.DecodedJWT;
import com.fasterxml.jackson.core.JsonProcessingException;
import java.io.IOException;
import java.net.URI;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Calendar;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.UUID;
import java.util.function.Predicate;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.http.client.HttpResponseException;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInfo;
import org.junit.jupiter.api.TestMethodOrder;
import org.openmetadata.catalog.Entity;
import org.openmetadata.catalog.api.teams.CreateUser;
import org.openmetadata.catalog.entity.data.Table;
import org.openmetadata.catalog.entity.teams.Role;
import org.openmetadata.catalog.entity.teams.Team;
import org.openmetadata.catalog.entity.teams.User;
import org.openmetadata.catalog.resources.EntityResourceTest;
import org.openmetadata.catalog.resources.databases.TableResourceTest;
import org.openmetadata.catalog.resources.locations.LocationResourceTest;
import org.openmetadata.catalog.resources.teams.UserResource.UserList;
import org.openmetadata.catalog.security.AuthenticationException;
import org.openmetadata.catalog.teams.authn.GenerateTokenRequest;
import org.openmetadata.catalog.teams.authn.JWTAuthMechanism;
import org.openmetadata.catalog.teams.authn.JWTTokenExpiry;
import org.openmetadata.catalog.type.ChangeDescription;
import org.openmetadata.catalog.type.EntityReference;
import org.openmetadata.catalog.type.FieldChange;
import org.openmetadata.catalog.type.ImageList;
import org.openmetadata.catalog.type.MetadataOperation;
import org.openmetadata.catalog.type.Profile;
import org.openmetadata.catalog.util.EntityUtil;
import org.openmetadata.catalog.util.JsonUtils;
import org.openmetadata.catalog.util.ResultList;
import org.openmetadata.catalog.util.TestUtils;
import org.openmetadata.catalog.util.TestUtils.UpdateType;

@Slf4j
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class UserResourceTest extends EntityResourceTest<User, CreateUser> {
  final Profile PROFILE = new Profile().withImages(new ImageList().withImage(URI.create("http://image.com")));

  public UserResourceTest() {
    super(Entity.USER, User.class, UserList.class, "users", UserResource.FIELDS);
    this.supportsAuthorizedMetadataOperations = false;
  }

  public void setupUsers(TestInfo test) throws HttpResponseException {
    CreateUser create = createRequest(test).withRoles(List.of(DATA_CONSUMER_ROLE.getId()));
    USER1 = createEntity(create, ADMIN_AUTH_HEADERS);
    USER1_REF = USER1.getEntityReference();

    create = createRequest(test, 1).withRoles(List.of(DATA_CONSUMER_ROLE.getId()));
    USER2 = createEntity(create, ADMIN_AUTH_HEADERS);
    USER2_REF = USER2.getEntityReference();

    create = createRequest("user-data-steward", "", "", null).withRoles(List.of(DATA_STEWARD_ROLE.getId()));
    USER_WITH_DATA_STEWARD_ROLE = createEntity(create, ADMIN_AUTH_HEADERS);

    create = createRequest("user-data-consumer", "", "", null).withRoles(List.of(DATA_CONSUMER_ROLE.getId()));
    USER_WITH_DATA_CONSUMER_ROLE = createEntity(create, ADMIN_AUTH_HEADERS);

    // USER_TEAM21 is part of TEAM21
    create = createRequest(test, 2).withTeams(List.of(TEAM21.getId()));
    USER_TEAM21 = createEntity(create, ADMIN_AUTH_HEADERS);
    USER2_REF = USER2.getEntityReference();
  }

  @Test
  @Override
  public void post_entity_as_non_admin_401(TestInfo test) {
    // Override the method as a User can create a User entity for himself
    // during first time login without being an admin
  }

  @Test
  void post_userWithoutEmail_400_badRequest(TestInfo test) {
    // Create user with mandatory email field null
    CreateUser create = createRequest(test).withEmail(null);
    assertResponse(() -> createEntity(create, ADMIN_AUTH_HEADERS), BAD_REQUEST, "[email must not be null]");

    // Create user with mandatory email field empty
    create.withEmail("");
    assertResponseContains(
        () -> createEntity(create, ADMIN_AUTH_HEADERS), BAD_REQUEST, "email must match \"^\\S+@\\S+\\.\\S+$\"");
    assertResponseContains(
        () -> createEntity(create, ADMIN_AUTH_HEADERS), BAD_REQUEST, "email size must be between 6 and 127");

    // Create user with mandatory email field with invalid email address
    create.withEmail("invalidEmail");
    assertResponseContains(
        () -> createEntity(create, ADMIN_AUTH_HEADERS), BAD_REQUEST, "[email must match \"^\\S+@\\S+\\.\\S+$\"]");
  }

  @Test
  void post_validUser_200_ok_without_login(TestInfo test) {
    CreateUser create =
        createRequest(test, 6).withDisplayName("displayName").withEmail("test@email.com").withIsAdmin(true);

    assertResponse(
        () -> createAndCheckEntity(create, null), UNAUTHORIZED, "Not authorized; User's Email is not present");
  }

  @Test
  void post_validUser_200_ok(TestInfo test) throws IOException {
    // Create user with different optional fields
    CreateUser create = createRequest(test, 1);
    createAndCheckEntity(create, ADMIN_AUTH_HEADERS);

    create = createRequest(test, 2).withDisplayName("displayName");
    createAndCheckEntity(create, ADMIN_AUTH_HEADERS);

    create = createRequest(test, 3).withProfile(PROFILE);
    createAndCheckEntity(create, ADMIN_AUTH_HEADERS);

    create = createRequest(test, 5).withDisplayName("displayName").withProfile(PROFILE).withIsBot(true);
    createAndCheckEntity(create, ADMIN_AUTH_HEADERS);

    create = createRequest(test, 6).withDisplayName("displayName").withProfile(PROFILE).withIsAdmin(true);
    createAndCheckEntity(create, ADMIN_AUTH_HEADERS);
  }

  @Test
  void put_validUser_200_ok() throws IOException {
    // Create user with different optional fields
    CreateUser create = createRequest("user.xyz", null, null, null);
    User user = updateAndCheckEntity(create, CREATED, ADMIN_AUTH_HEADERS, UpdateType.CREATED, null);

    // Update the user information using PUT
    String oldEmail = create.getEmail();
    CreateUser update = create.withEmail("test1@email.com").withDisplayName("displayName1");

    ChangeDescription change = getChangeDescription(user.getVersion());
    change.getFieldsAdded().add(new FieldChange().withName("displayName").withNewValue("displayName1"));
    change
        .getFieldsUpdated()
        .add(new FieldChange().withName("email").withOldValue(oldEmail).withNewValue("test1@email.com"));
    updateAndCheckEntity(update, OK, ADMIN_AUTH_HEADERS, MINOR_UPDATE, change);
  }

  @Test
  void post_validAdminUser_Non_Admin_401(TestInfo test) {
    CreateUser create =
        createRequest(test, 6)
            .withName("test")
            .withDisplayName("displayName")
            .withEmail("test@email.com")
            .withIsAdmin(true);

    assertResponse(() -> createAndCheckEntity(create, TEST_AUTH_HEADERS), FORBIDDEN, notAdmin(TEST_USER_NAME));
  }

  @Test
  void post_validAdminUser_200_ok(TestInfo test) throws IOException {
    CreateUser create =
        createRequest(test, 6)
            .withName("testAdmin")
            .withDisplayName("displayName")
            .withEmail("testAdmin@email.com")
            .withIsAdmin(true);
    createAndCheckEntity(create, ADMIN_AUTH_HEADERS);
  }

  @Test
  void post_validUserWithTeams_200_ok(TestInfo test) throws IOException {
    // Create user with different optional fields
    TeamResourceTest teamResourceTest = new TeamResourceTest();
    Team team1 = teamResourceTest.createEntity(teamResourceTest.createRequest(test, 1), ADMIN_AUTH_HEADERS);
    Team team2 = teamResourceTest.createEntity(teamResourceTest.createRequest(test, 2), ADMIN_AUTH_HEADERS);
    List<UUID> teams = Arrays.asList(team1.getId(), team2.getId());
    CreateUser create = createRequest(test).withTeams(teams);
    User user = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);

    // Ensure Team has relationship to this user
    team1 = teamResourceTest.getEntity(team1.getId(), "users", ADMIN_AUTH_HEADERS);
    assertEquals(user.getId(), team1.getUsers().get(0).getId());
    team2 = teamResourceTest.getEntity(team2.getId(), "users", ADMIN_AUTH_HEADERS);
    assertEquals(user.getId(), team2.getUsers().get(0).getId());
  }

  @Test
  void post_validUserWithRoles_200_ok(TestInfo test) throws IOException {
    // Create user with different optional fields
    RoleResourceTest roleResourceTest = new RoleResourceTest();
    Role role1 = roleResourceTest.createEntity(roleResourceTest.createRequest(test, 1), ADMIN_AUTH_HEADERS);
    Role role2 = roleResourceTest.createEntity(roleResourceTest.createRequest(test, 2), ADMIN_AUTH_HEADERS);
    List<UUID> roles = Arrays.asList(role1.getId(), role2.getId());
    CreateUser create = createRequest(test).withRoles(roles);
    List<UUID> createdRoles = Arrays.asList(role1.getId(), role2.getId());
    CreateUser created = createRequest(test).withRoles(createdRoles);
    User user = createAndCheckEntity(create, ADMIN_AUTH_HEADERS, created);

    // Ensure User has relationship to these roles
    String[] expectedRoles = createdRoles.stream().map(UUID::toString).sorted().toArray(String[]::new);
    List<EntityReference> roleReferences = user.getRoles();
    String[] actualRoles = roleReferences.stream().map(ref -> ref.getId().toString()).sorted().toArray(String[]::new);
    assertArrayEquals(expectedRoles, actualRoles);
  }

  @Test
  void get_listUsersWithTeams_200_ok(TestInfo test) throws IOException {
    TeamResourceTest teamResourceTest = new TeamResourceTest();
    Team team1 = teamResourceTest.createEntity(teamResourceTest.createRequest(test, 1), ADMIN_AUTH_HEADERS);
    Team team2 = teamResourceTest.createEntity(teamResourceTest.createRequest(test, 2), ADMIN_AUTH_HEADERS);
    List<UUID> teams = of(team1.getId(), team2.getId());
    List<UUID> team = of(team1.getId());

    // user0 is part of no teams
    // user1 is part of team1
    // user2 is part of team1, and team2
    CreateUser create = createRequest(test, 0);
    User user0 = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);
    create = createRequest(test, 1).withTeams(team);
    User user1 = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);
    create = createRequest(test, 2).withTeams(teams);
    User user2 = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);

    Predicate<User> isUser0 = u -> u.getId().equals(user0.getId());
    Predicate<User> isUser1 = u -> u.getId().equals(user1.getId());
    Predicate<User> isUser2 = u -> u.getId().equals(user2.getId());

    Map<String, String> queryParams = new HashMap<>();
    queryParams.put("team", team1.getName());

    ResultList<User> users = listEntities(queryParams, 100_000, null, null, ADMIN_AUTH_HEADERS);
    assertEquals(2, users.getData().size());
    assertTrue(users.getData().stream().anyMatch(isUser1));
    assertTrue(users.getData().stream().anyMatch(isUser2));

    queryParams = new HashMap<>();
    queryParams.put("team", team2.getName());

    users = listEntities(queryParams, 100_000, null, null, ADMIN_AUTH_HEADERS);
    assertEquals(1, users.getData().size());
    assertTrue(users.getData().stream().anyMatch(isUser2));

    users = listEntities(null, 100_000, null, null, ADMIN_AUTH_HEADERS);
    assertTrue(users.getData().stream().anyMatch(isUser0));
    assertTrue(users.getData().stream().anyMatch(isUser1));
    assertTrue(users.getData().stream().anyMatch(isUser2));
  }

  @Test
  void get_listUsersWithAdminFilter_200_ok(TestInfo test) throws IOException {
    ResultList<User> users = listEntities(null, 100_000, null, null, ADMIN_AUTH_HEADERS);
    int initialUserCount = users.getPaging().getTotal();
    Map<String, String> adminQueryParams = new HashMap<>();
    adminQueryParams.put("isAdmin", "true");
    users = listEntities(adminQueryParams, 100_000, null, null, ADMIN_AUTH_HEADERS);
    int initialAdminCount = users.getPaging().getTotal();

    // user0 is admin
    // user1 is not an admin
    // user2 is not an admin
    CreateUser create = createRequest(test, 0).withIsAdmin(true);
    User user0 = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);
    create = createRequest(test, 1).withIsAdmin(false);
    User user1 = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);
    create = createRequest(test, 2).withIsAdmin(false);
    User user2 = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);

    Predicate<User> isUser0 = u -> u.getId().equals(user0.getId());
    Predicate<User> isUser1 = u -> u.getId().equals(user1.getId());
    Predicate<User> isUser2 = u -> u.getId().equals(user2.getId());

    users = listEntities(null, 100_000, null, null, ADMIN_AUTH_HEADERS);
    assertEquals(initialUserCount + 3, users.getPaging().getTotal());

    // list admin users
    users = listEntities(adminQueryParams, 100_000, null, null, ADMIN_AUTH_HEADERS);
    assertEquals(initialAdminCount + 1, users.getData().size());
    assertEquals(initialAdminCount + 1, users.getPaging().getTotal());
    assertTrue(users.getData().stream().anyMatch(isUser0));

    Map<String, String> queryParams = new HashMap<>();
    queryParams.put("isAdmin", "false");

    // list non-admin users
    users = listEntities(queryParams, 100_000, null, null, ADMIN_AUTH_HEADERS);
    assertEquals(initialUserCount - initialAdminCount + 2, users.getPaging().getTotal());
    assertTrue(users.getData().stream().anyMatch(isUser1));
    assertTrue(users.getData().stream().anyMatch(isUser2));
  }

  @Test
  void get_listUsersWithBotFilter_200_ok(TestInfo test) throws IOException {
    ResultList<User> users = listEntities(null, 100_000, null, null, ADMIN_AUTH_HEADERS);
    int initialUserCount = users.getPaging().getTotal();
    Map<String, String> botQueryParams = new HashMap<>();
    botQueryParams.put("isBot", "true");
    ResultList<User> bots = listEntities(botQueryParams, 100_000, null, null, ADMIN_AUTH_HEADERS);
    int initialBotCount = bots.getPaging().getTotal();

    // Create 3 bot users
    CreateUser create = createRequest(test, 0).withIsBot(true);
    User bot0 = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);
    create = createRequest(test, 1).withIsBot(true);
    User bot1 = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);
    create = createRequest(test, 2).withIsBot(true);
    User bot2 = createAndCheckEntity(create, ADMIN_AUTH_HEADERS);

    Predicate<User> isBot0 = u -> u.getId().equals(bot0.getId());
    Predicate<User> isBot1 = u -> u.getId().equals(bot1.getId());
    Predicate<User> isBot2 = u -> u.getId().equals(bot2.getId());

    users = listEntities(null, 100_000, null, null, ADMIN_AUTH_HEADERS);
    assertEquals(initialUserCount + 3, users.getPaging().getTotal());

    // list bot users
    bots = listEntities(botQueryParams, 100_000, null, null, ADMIN_AUTH_HEADERS);
    assertEquals(initialBotCount + 3, bots.getData().size());
    assertEquals(initialBotCount + 3, bots.getPaging().getTotal());
    assertTrue(bots.getData().stream().anyMatch(isBot0));
    assertTrue(bots.getData().stream().anyMatch(isBot1));
    assertTrue(bots.getData().stream().anyMatch(isBot2));

    Map<String, String> queryParams = new HashMap<>();
    queryParams.put("isBot", "false");

    // list users (not bots)
    users = listEntities(queryParams, 100_000, null, null, ADMIN_AUTH_HEADERS);
    assertEquals(initialUserCount - initialBotCount, users.getPaging().getTotal());
  }

  @Test
  void get_listUsersWithTeamsPagination(TestInfo test) throws IOException {
    TeamResourceTest teamResourceTest = new TeamResourceTest();
    Team team1 = teamResourceTest.createEntity(teamResourceTest.createRequest(test, 1), ADMIN_AUTH_HEADERS);
    List<UUID> team = of(team1.getId());

    // create 15 users and add them to team1
    for (int i = 0; i < 15; i++) {
      CreateUser create = createRequest(test, i).withTeams(team);
      createAndCheckEntity(create, ADMIN_AUTH_HEADERS);
    }

    Map<String, String> queryParams = new HashMap<>();
    queryParams.put("team", team1.getName());

    ResultList<User> users = listEntities(queryParams, 5, null, null, ADMIN_AUTH_HEADERS);
    assertEquals(5, users.getData().size());
    assertEquals(15, users.getPaging().getTotal());
    // First page must contain "after" and should not have "before"
    assertNotNull(users.getPaging().getAfter());
    assertNull(users.getPaging().getBefore());
    User user1 = users.getData().get(0);

    String after = users.getPaging().getAfter();
    users = listEntities(queryParams, 5, null, after, ADMIN_AUTH_HEADERS);
    assertEquals(5, users.getData().size());
    assertEquals(15, users.getPaging().getTotal());
    // Second page must contain both "after" and "before"
    assertNotNull(users.getPaging().getAfter());
    assertNotNull(users.getPaging().getBefore());
    User user2 = users.getData().get(0);

    after = users.getPaging().getAfter();
    users = listEntities(queryParams, 5, null, after, ADMIN_AUTH_HEADERS);
    assertEquals(5, users.getData().size());
    assertEquals(15, users.getPaging().getTotal());
    // Third page must contain only "before" since it is the last page
    assertNull(users.getPaging().getAfter());
    assertNotNull(users.getPaging().getBefore());
    User user3 = users.getData().get(0);
    assertNotEquals(user2, user3);

    // Now fetch previous pages using before pointer
    String before = users.getPaging().getBefore();
    users = listEntities(queryParams, 5, before, null, ADMIN_AUTH_HEADERS);
    assertEquals(5, users.getData().size());
    assertEquals(15, users.getPaging().getTotal());
    // Second page must contain both "after" and "before"
    assertNotNull(users.getPaging().getAfter());
    assertNotNull(users.getPaging().getBefore());
    assertEquals(user2, users.getData().get(0));

    before = users.getPaging().getBefore();
    users = listEntities(queryParams, 5, before, null, ADMIN_AUTH_HEADERS);
    assertEquals(5, users.getData().size());
    assertEquals(15, users.getPaging().getTotal());
    // First page must contain only "after"
    assertNotNull(users.getPaging().getAfter());
    assertNull(users.getPaging().getBefore());
    assertEquals(user1, users.getData().get(0));
  }

  /**
   * @see EntityResourceTest put_addDeleteFollower_200 test for tests related to GET user with owns field parameter
   * @see EntityResourceTest put_addDeleteFollower_200 for tests related getting user with follows list
   * @see TableResourceTest also tests GET user returns owns list
   */
  @Test
  void patch_userNameChange_as_another_user_401(TestInfo test) throws HttpResponseException, JsonProcessingException {
    // Ensure user display can't be changed using patch by another user
    User user =
        createEntity(
            createRequest(test, 7).withName("test23").withDisplayName("displayName").withEmail("test23@email.com"),
            authHeaders("test23@email.com"));
    String userJson = JsonUtils.pojoToJson(user);
    user.setDisplayName("newName");
    assertResponse(
        () -> patchEntity(user.getId(), userJson, user, TEST_AUTH_HEADERS),
        FORBIDDEN,
        permissionNotAllowed(TEST_USER_NAME, List.of(MetadataOperation.EDIT_DISPLAY_NAME)));
  }

  @Test
  void patch_makeAdmin_as_another_user_401(TestInfo test) throws HttpResponseException, JsonProcessingException {
    // Ensure username can't be changed using patch
    User user =
        createEntity(
            createRequest(test, 6).withName("test2").withDisplayName("displayName").withEmail("test2@email.com"),
            authHeaders("test2@email.com"));
    String userJson = JsonUtils.pojoToJson(user);
    user.setIsAdmin(Boolean.TRUE);
    assertResponse(() -> patchEntity(user.getId(), userJson, user, TEST_AUTH_HEADERS), FORBIDDEN, notAdmin("test"));
  }

  @Test
  void patch_userNameChange_as_same_user_200_ok(TestInfo test) throws HttpResponseException, JsonProcessingException {
    // Ensure username can't be changed using patch
    User user =
        createEntity(
            createRequest(test, 6).withName("test1").withDisplayName("displayName").withEmail("test1@email.com"),
            authHeaders("test1@email.com"));
    String userJson = JsonUtils.pojoToJson(user);
    String newDisplayName = "newDisplayName";
    user.setDisplayName(newDisplayName); // Update the name
    user = patchEntity(user.getId(), userJson, user, ADMIN_AUTH_HEADERS); // Patch the user
    assertEquals(newDisplayName, user.getDisplayName());
  }

  @Test
  void patch_userAttributes_as_admin_200_ok(TestInfo test) throws IOException {
    // Create user without any attributes - ***Note*** isAdmin by default is false.
    User user = createEntity(createRequest(test).withProfile(null), ADMIN_AUTH_HEADERS);
    assertListNull(user.getDisplayName(), user.getIsBot(), user.getProfile(), user.getTimezone());

    TeamResourceTest teamResourceTest = new TeamResourceTest();
    EntityReference team1 =
        teamResourceTest.createEntity(teamResourceTest.createRequest(test, 1), ADMIN_AUTH_HEADERS).getEntityReference();
    EntityReference team2 =
        teamResourceTest.createEntity(teamResourceTest.createRequest(test, 2), ADMIN_AUTH_HEADERS).getEntityReference();
    EntityReference team3 =
        teamResourceTest.createEntity(teamResourceTest.createRequest(test, 3), ADMIN_AUTH_HEADERS).getEntityReference();
    List<EntityReference> teams = Arrays.asList(team1, team2);
    Profile profile = new Profile().withImages(new ImageList().withImage(URI.create("http://image.com")));

    RoleResourceTest roleResourceTest = new RoleResourceTest();
    EntityReference role1 =
        roleResourceTest.createEntity(roleResourceTest.createRequest(test, 1), ADMIN_AUTH_HEADERS).getEntityReference();

    //
    // Add previously absent attributes. Note the default team Organization is deleted when adding new teams.
    //
    String origJson = JsonUtils.pojoToJson(user);

    String timezone = "America/Los_Angeles";
    user.withRoles(Arrays.asList(role1))
        .withTeams(teams)
        .withTimezone(timezone)
        .withDisplayName("displayName")
        .withProfile(profile)
        .withIsBot(false)
        .withIsAdmin(false);
    ChangeDescription change = getChangeDescription(user.getVersion());
    change.getFieldsAdded().add(new FieldChange().withName("roles").withNewValue(Arrays.asList(role1)));
    change
        .getFieldsDeleted()
        .add(new FieldChange().withName("teams").withOldValue(Arrays.asList(ORG_TEAM.getEntityReference())));
    change.getFieldsAdded().add(new FieldChange().withName("teams").withNewValue(teams));
    change.getFieldsAdded().add(new FieldChange().withName("timezone").withNewValue(timezone));
    change.getFieldsAdded().add(new FieldChange().withName("displayName").withNewValue("displayName"));
    change.getFieldsAdded().add(new FieldChange().withName("profile").withNewValue(profile));
    change.getFieldsAdded().add(new FieldChange().withName("isBot").withNewValue(false));
    user = patchEntityAndCheck(user, origJson, ADMIN_AUTH_HEADERS, MINOR_UPDATE, change);

    //
    // Replace the attributes
    //
    String timezone1 = "Canada/Eastern";
    List<EntityReference> teams1 = Arrays.asList(team1, team3); // team2 dropped and team3 is added
    Profile profile1 = new Profile().withImages(new ImageList().withImage(URI.create("http://image2.com")));

    EntityReference role2 =
        roleResourceTest.createEntity(roleResourceTest.createRequest(test, 2), ADMIN_AUTH_HEADERS).getEntityReference();

    origJson = JsonUtils.pojoToJson(user);
    user.withRoles(Arrays.asList(role2))
        .withTeams(teams1)
        .withTimezone(timezone1)
        .withDisplayName("displayName1")
        .withProfile(profile1)
        .withIsBot(true)
        .withIsAdmin(false);

    change = getChangeDescription(user.getVersion());
    change.getFieldsDeleted().add(new FieldChange().withName("roles").withOldValue(Arrays.asList(role1)));
    change.getFieldsAdded().add(new FieldChange().withName("roles").withNewValue(Arrays.asList(role2)));
    change.getFieldsDeleted().add(new FieldChange().withName("teams").withOldValue(of(team2)));
    change.getFieldsAdded().add(new FieldChange().withName("teams").withNewValue(of(team3)));
    change
        .getFieldsUpdated()
        .add(new FieldChange().withName("timezone").withOldValue(timezone).withNewValue(timezone1));
    change
        .getFieldsUpdated()
        .add(new FieldChange().withName("displayName").withOldValue("displayName").withNewValue("displayName1"));
    change.getFieldsUpdated().add(new FieldChange().withName("profile").withOldValue(profile).withNewValue(profile1));
    change.getFieldsUpdated().add(new FieldChange().withName("isBot").withOldValue(false).withNewValue(true));
    user = patchEntityAndCheck(user, origJson, ADMIN_AUTH_HEADERS, MINOR_UPDATE, change);

    //
    // Remove the attributes
    //
    origJson = JsonUtils.pojoToJson(user);
    user.withRoles(null)
        .withTeams(null)
        .withTimezone(null)
        .withDisplayName(null)
        .withProfile(null)
        .withIsBot(null)
        .withIsAdmin(false);

    // Note non-empty display field is not deleted. When teams are deleted, Organization is added back as default team.
    change = getChangeDescription(user.getVersion());
    change.getFieldsDeleted().add(new FieldChange().withName("roles").withOldValue(Arrays.asList(role2)));
    change.getFieldsDeleted().add(new FieldChange().withName("teams").withOldValue(teams1));
    change
        .getFieldsAdded()
        .add(new FieldChange().withName("teams").withNewValue(Arrays.asList(ORG_TEAM.getEntityReference())));
    change.getFieldsDeleted().add(new FieldChange().withName("timezone").withOldValue(timezone1));
    change.getFieldsDeleted().add(new FieldChange().withName("displayName").withOldValue("displayName1"));
    change.getFieldsDeleted().add(new FieldChange().withName("profile").withOldValue(profile1));
    change.getFieldsDeleted().add(new FieldChange().withName("isBot").withOldValue(true).withNewValue(null));
    patchEntityAndCheck(user, origJson, ADMIN_AUTH_HEADERS, MINOR_UPDATE, change);
  }

  @Test
  void delete_validUser_as_admin_200(TestInfo test) throws IOException {
    TeamResourceTest teamResourceTest = new TeamResourceTest();
    Team team = teamResourceTest.createEntity(teamResourceTest.createRequest(test), ADMIN_AUTH_HEADERS);
    List<UUID> teamIds = Collections.singletonList(team.getId());

    // Create user with teams
    CreateUser create = createRequest(test).withProfile(PROFILE).withTeams(teamIds);
    User user = createEntity(create, ADMIN_AUTH_HEADERS);

    // Add user as follower to a table
    TableResourceTest tableResourceTest = new TableResourceTest();
    Table table = tableResourceTest.createEntity(test, 1);
    tableResourceTest.addAndCheckFollower(table.getId(), user.getId(), OK, 1, ADMIN_AUTH_HEADERS);

    // Delete user
    deleteAndCheckEntity(user, ADMIN_AUTH_HEADERS);

    // Make sure the user is no longer following the table
    team = teamResourceTest.getEntity(team.getId(), "users", ADMIN_AUTH_HEADERS);
    assertDeleted(team.getUsers(), true);
    tableResourceTest.checkFollowerDeleted(table.getId(), user.getId(), ADMIN_AUTH_HEADERS);

    // User can no longer follow other entities
    assertResponse(
        () -> tableResourceTest.addAndCheckFollower(table.getId(), user.getId(), OK, 1, ADMIN_AUTH_HEADERS),
        NOT_FOUND,
        entityNotFound("user", user.getId()));
  }

  @Test
  void put_generateToken_bot_user_200_ok(TestInfo test) throws HttpResponseException {
    User user =
        createEntity(
            createRequest(test, 6)
                .withName("ingestion-bot-jwt")
                .withDisplayName("ingestion-bot-jwt")
                .withEmail("ingestion-bot-jwt@email.com")
                .withIsBot(true),
            authHeaders("ingestion-bot-jwt@email.com"));
    TestUtils.put(
        getResource(String.format("users/generateToken/%s", user.getId())),
        new GenerateTokenRequest().withJWTTokenExpiry(JWTTokenExpiry.Seven),
        OK,
        ADMIN_AUTH_HEADERS);
    user = getEntity(user.getId(), ADMIN_AUTH_HEADERS);
    assertNull(user.getAuthenticationMechanism());
    JWTAuthMechanism jwtAuthMechanism =
        TestUtils.get(
            getResource(String.format("users/token/%s", user.getId())), JWTAuthMechanism.class, ADMIN_AUTH_HEADERS);
    assertNotNull(jwtAuthMechanism.getJWTToken());
    DecodedJWT jwt = decodedJWT(jwtAuthMechanism.getJWTToken());
    Date date = jwt.getExpiresAt();
    long daysBetween = ((date.getTime() - jwt.getIssuedAt().getTime()) / (1000 * 60 * 60 * 24));
    assertTrue(daysBetween >= 6);
    assertEquals("ingestion-bot-jwt", jwt.getClaims().get("sub").asString());
    assertEquals(true, jwt.getClaims().get("isBot").asBoolean());
    TestUtils.put(getResource(String.format("users/revokeToken/%s", user.getId())), User.class, OK, ADMIN_AUTH_HEADERS);
    jwtAuthMechanism =
        TestUtils.get(
            getResource(String.format("users/token/%s", user.getId())), JWTAuthMechanism.class, ADMIN_AUTH_HEADERS);
    assertEquals(StringUtils.EMPTY, jwtAuthMechanism.getJWTToken());
  }

  @Test
  void testInheritedRole() throws HttpResponseException {
    // USER1 inherits DATA_CONSUMER_ROLE from Organization
    User user1 = getEntity(USER1.getId(), "roles", ADMIN_AUTH_HEADERS);
    assertEntityReferences(List.of(DATA_CONSUMER_ROLE_REF), user1.getInheritedRoles());

    // USER_TEAM21 inherits DATA_CONSUMER_ROLE from Organization and DATA_STEWARD_ROLE from Team2
    User user_team21 = getEntity(USER_TEAM21.getId(), "roles", ADMIN_AUTH_HEADERS);
    assertEntityReferences(List.of(DATA_CONSUMER_ROLE_REF, DATA_STEWARD_ROLE_REF), user_team21.getInheritedRoles());
  }

  private DecodedJWT decodedJWT(String token) {
    DecodedJWT jwt;
    try {
      jwt = JWT.decode(token);
    } catch (JWTDecodeException e) {
      throw new AuthenticationException("Invalid token", e);
    }

    // Check if expired
    // if the expiresAt set to null, treat it as never expiring token
    if (jwt.getExpiresAt() != null
        && jwt.getExpiresAt().before(Calendar.getInstance(TimeZone.getTimeZone("UTC")).getTime())) {
      throw new AuthenticationException("Expired token!");
    }

    return jwt;
  }

  private void assertRoles(User user, List<EntityReference> expectedRoles) {
    TestUtils.assertEntityReferences(expectedRoles, user.getRoles());
  }

  @Override
  public User validateGetWithDifferentFields(User user, boolean byName) throws HttpResponseException {
    String fields = "";
    user =
        byName
            ? getEntityByName(user.getName(), fields, ADMIN_AUTH_HEADERS)
            : getEntity(user.getId(), fields, ADMIN_AUTH_HEADERS);
    assertListNull(user.getProfile(), user.getRoles(), user.getTeams(), user.getFollows(), user.getOwns());

    fields = "profile,roles,teams,follows,owns";
    user =
        byName
            ? getEntityByName(user.getName(), fields, ADMIN_AUTH_HEADERS)
            : getEntity(user.getId(), fields, ADMIN_AUTH_HEADERS);
    assertListNotNull(user.getProfile(), user.getRoles(), user.getTeams(), user.getFollows(), user.getOwns());
    validateAlphabeticalOrdering(user.getTeams(), EntityUtil.compareEntityReference);
    return user;
  }

  @Override
  public CreateUser createRequest(String name) {
    // user part of the email should be less than 64 in length
    String emailUser = nullOrEmpty(name) ? UUID.randomUUID().toString() : name;
    emailUser = emailUser.length() > 64 ? emailUser.substring(0, 64) : emailUser;
    return new CreateUser().withName(name).withEmail(emailUser + "@open-metadata.org").withProfile(PROFILE);
  }

  @Override
  public User beforeDeletion(TestInfo test, User user) throws HttpResponseException {
    LocationResourceTest locationResourceTest = new LocationResourceTest();
    EntityReference userRef = new EntityReference().withId(user.getId()).withType("user");
    locationResourceTest.createEntity(
        locationResourceTest.createRequest(getEntityName(test, 0), null, null, userRef), ADMIN_AUTH_HEADERS);
    locationResourceTest.createEntity(
        locationResourceTest.createRequest(getEntityName(test, 1), null, null, TEAM11_REF), ADMIN_AUTH_HEADERS);
    return user;
  }

  @Override
  protected void validateDeletedEntity(
      CreateUser create, User userBeforeDeletion, User userAfterDeletion, Map<String, String> authHeaders)
      throws HttpResponseException {
    super.validateDeletedEntity(create, userBeforeDeletion, userAfterDeletion, authHeaders);

    List<EntityReference> expectedOwnedEntities = new ArrayList<>();
    for (EntityReference ref : listOrEmpty(userBeforeDeletion.getOwns())) {
      expectedOwnedEntities.add(new EntityReference().withId(ref.getId()).withType(Entity.TABLE));
    }

    TestUtils.assertEntityReferences(expectedOwnedEntities, userAfterDeletion.getOwns());
  }

  @Override
  public void validateCreatedEntity(User user, CreateUser createRequest, Map<String, String> authHeaders)
      throws HttpResponseException {
    assertEquals(createRequest.getName(), user.getName());
    assertEquals(createRequest.getDisplayName(), user.getDisplayName());
    assertEquals(createRequest.getTimezone(), user.getTimezone());
    assertEquals(createRequest.getIsBot(), user.getIsBot());
    assertEquals(createRequest.getIsAdmin(), user.getIsAdmin());

    List<EntityReference> expectedRoles = new ArrayList<>();
    for (UUID roleId : listOrEmpty(createRequest.getRoles())) {
      expectedRoles.add(new EntityReference().withId(roleId).withType(Entity.ROLE));
    }
    assertRoles(user, expectedRoles);

    List<EntityReference> expectedTeams = new ArrayList<>();
    for (UUID teamId : listOrEmpty(createRequest.getTeams())) {
      expectedTeams.add(new EntityReference().withId(teamId).withType(Entity.TEAM));
    }
    if (expectedTeams.isEmpty()) {
      expectedTeams = new ArrayList<>(List.of(ORG_TEAM.getEntityReference())); // Organization is default team
    }
    assertEntityReferences(expectedTeams, user.getTeams());

    if (createRequest.getProfile() != null) {
      assertEquals(createRequest.getProfile(), user.getProfile());
    }
  }

  @Override
  public void compareEntities(User expected, User updated, Map<String, String> authHeaders) {
    assertEquals(expected.getName(), expected.getName());
    assertEquals(expected.getDisplayName(), expected.getDisplayName());
    assertEquals(expected.getTimezone(), expected.getTimezone());
    assertEquals(expected.getIsBot(), expected.getIsBot());
    assertEquals(expected.getIsAdmin(), expected.getIsAdmin());

    TestUtils.assertEntityReferences(expected.getRoles(), updated.getRoles());
    TestUtils.assertEntityReferences(expected.getTeams(), updated.getTeams());

    if (expected.getProfile() != null) {
      assertEquals(expected.getProfile(), updated.getProfile());
    }
  }

  @Override
  public void assertFieldChange(String fieldName, Object expected, Object actual) throws IOException {
    if (expected == null && actual == null) {
      return;
    }
    if (fieldName.equals("profile")) {
      Profile expectedProfile = (Profile) expected;
      Profile actualProfile = JsonUtils.readValue(actual.toString(), Profile.class);
      assertEquals(expectedProfile, actualProfile);
    } else if (fieldName.equals("teams") || fieldName.equals("roles")) {
      @SuppressWarnings("unchecked")
      List<EntityReference> expectedList = (List<EntityReference>) expected;
      List<EntityReference> actualList = JsonUtils.readObjects(actual.toString(), EntityReference.class);
      assertEntityReferences(expectedList, actualList);
    } else {
      assertCommonFieldChange(fieldName, expected, actual);
    }
  }
}
