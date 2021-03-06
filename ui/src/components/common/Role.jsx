import React, { Component } from 'react';
import {connect} from 'react-redux';
import { defineMessages, injectIntl } from 'react-intl';
import { Link } from 'react-router-dom';
import { Button, MenuItem, Position, Classes, Alignment } from "@blueprintjs/core";
import { Select as BlueprintSelect } from "@blueprintjs/select";

import wordList from 'src/util/wordList';
import { suggestRoles } from "src/actions";

import './Role.scss';
import Icon from "./Icon";

const messages = defineMessages({
  label: {
    id: 'role.select.user',
    defaultMessage: 'Choose a user',
  },
  suggest_initial: {
    id: 'role.begin.typing',
    defaultMessage: 'Search by name or email',
  },
  no_results: {
    id: 'role.no.results',
    defaultMessage: 'No match, keep typing',
  }
});


class RoleLabel extends Component {
  shouldComponentUpdate(nextProps) {
    return this.props.role.id !== nextProps.role.id;
  }

  render() {
    const { role, icon = true, long = false } = this.props;
    if (!role) {
      return null;
    }
    return (
      <React.Fragment>
        { icon && (
          <React.Fragment>
            <Icon name="person"/>
            {' '}
          </React.Fragment>
        )}
        { long ? role.label : role.name }
      </React.Fragment>
    );
  }
}


class RoleLink extends Component {
  render() {
    const { role } = this.props;
    if (!role) {
      return null;
    }
    return (
      <Link to={'/sources?collectionsfilter:team.id=' + role.id}>
        <RoleLabel {...this.props} />
      </Link>
    );
  }
}


class RoleList extends Component {
  render() {
    const { roles, truncate = Infinity } = this.props;
    if (!roles) return null;

    let names = roles.map((role, i) => {
      return <RoleLink key={role.id} role={role} {...this.props} />;
    });

    // Truncate if too long
    if (names.length > truncate) {
      names = [...names.slice(0, truncate), '…'];
    }
    return wordList(names, ' · ');
  }
}


class Select extends Component {

  constructor(props) {
    super(props);
    this.state = {
      suggested: [],
    };
    this.renderRole = this.renderRole.bind(this);
    this.onSuggest = this.onSuggest.bind(this);
    this.onSelectRole = this.onSelectRole.bind(this);
  }

  async onSuggest(query) {
    if (query.length <= 3) {
      return;
    }
    const { exclude = [] } = this.props;
    const roles = await this.props.suggestRoles(query, exclude);
    this.setState({
      suggested: roles.results
    })
  }

  onSelectRole(role, event) {
    event.stopPropagation();
    this.props.onSelect(role);
  }

  renderRole(role, { handleClick, modifiers }) {
    return <MenuItem className={modifiers.active ? Classes.ACTIVE : ""}
                     key={role.id}
                     onClick={handleClick}
                     text={role.label} />;
  }

  render () {
    const { intl, role } = this.props;
    const { suggested } = this.state;
    const label = role ? role.label : intl.formatMessage(messages.label);
  
    return <BlueprintSelect
              initialContent={
                <MenuItem disabled={true} text={intl.formatMessage(messages.suggest_initial)} />
              }
              noResults={
                <MenuItem disabled={true} text={intl.formatMessage(messages.no_results)} />
              }
              itemRenderer={this.renderRole}
              items={suggested}
              onItemSelect={this.onSelectRole}
              onQueryChange={this.onSuggest}
              popoverProps={{
                position: Position.BOTTOM_LEFT,
                className: "RoleSelect",
                usePortal: false
              }}
              filterable={true}
              resetOnClose={true}
              resetOnSelect={true}>
      <Button text={label}
              fill={true}
              alignText={Alignment.LEFT}
              rightIcon="search" />
    </BlueprintSelect>;
  }  
}


class Role {
  static Label = RoleLabel;
  static Link = RoleLink;
  static List = RoleList;
  static Select = connect(null, {suggestRoles})(injectIntl(Select));;
}

export default Role;
