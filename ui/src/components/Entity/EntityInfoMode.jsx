import React, {Component} from 'react';
import _ from "lodash";

import { Property } from 'src/components/common';
import { selectSchemata } from "../../selectors";
import { connect } from "react-redux";


class EntityInfoMode extends Component {
  render() {
    const { entity, schema } = this.props;
    if (schema === undefined) {
      return null;
    }

    const entityProperties = _.values(schema.properties).filter((prop) => {
      return !prop.caption && (schema.featured.indexOf(prop.name) !== -1 || entity.properties[prop.name]);
    });
    return (
      <ul className="info-sheet">
        { entityProperties.map((prop) => (
          <li key={prop.name}>
            <span className="key">
              <Property.Name model={prop} />
            </span>
            <span className="value">
              <Property.Values model={prop}
                               values={entity.properties[prop.name]} />
            </span>
          </li>
        ))}
      </ul>
    );
  }
}

const mapStateToProps = (state, ownProps) => {
  const { entity } = ownProps;
  return {
    schema: selectSchemata(state)[entity.schema]
  };
};

EntityInfoMode = connect(mapStateToProps, {})(EntityInfoMode);
export default EntityInfoMode;
