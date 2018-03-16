import React, { Component } from 'react';
import queryString from 'query-string';

import Country from 'src/components/common/Country';
import Schema from 'src/components/common/Schema';
import Collection from 'src/components/common/Collection';
import Entity from 'src/screens/EntityScreen/Entity';
import FileSize from 'src/components/common/FileSize';
import Date from 'src/components/common/Date';

class EntityTableRow extends Component {
  constructor(props) {
    super(props);
    this.onRowClickHandler = this.onRowClickHandler.bind(this);
  }

  onRowClickHandler(event) {
    // If showLinksInPreview enabled allows the user to click anywhere on the
    // row and have the row selected and preview open automatically.
    const { showLinksInPreview } = this.props;
    if (showLinksInPreview && showLinksInPreview === true) {
      // If the target that was clicked was not a link then find the the first 
      // link and simulate clicking the link in it, which will load the preview.
      // (If the target *was* a link does not do anything.)
      if (event.target.nodeName !== 'A') {
        const links = event.currentTarget.getElementsByTagName('a');
        if (links[0]) links[0].click();
      }
    }
  }  
  
  shouldComponentUpdate(nextProps) {
    // Only update if the ID of the entity has changed *or* location has updated
    if (this.props.entity.id !== nextProps.entity.id ||
        this.props.location !== nextProps.location) {
      return true;
    } else {
      return false;
    }
  }

  render() {
    const { entity, hideCollection, documentMode, showLinksInPreview, className, location: loc } = this.props;
    const parsedHash = queryString.parse(loc.hash);
    
    let rowClassName = (className) ? `${className} nowrap` : 'nowrap'

    // Select the current row if the ID of the entity matches the ID of the
    // current object being previewed. We do this so that if a link is shared
    // the currently displayed preview will also have the row it corresponds to
    // highlighted automatically.
    if (parsedHash['preview:id'] && parsedHash['preview:id'] === entity.id) {
      rowClassName += ' active'
    }
    
    return (
      <tr className={rowClassName} onClick={this.onRowClickHandler}>
        <td className="entity">
          <Entity.Link preview={showLinksInPreview} entity={entity} icon />
        </td>
        {!hideCollection && 
          <td className="collection">
            <Collection.Link preview={showLinksInPreview} collection={entity.collection} icon />
          </td>
        }
        <td className="schema">
          <Schema.Label schema={entity.schema} />
        </td>
        {!documentMode && (
          <td className="country">
            <Country.List codes={entity.countries} />
          </td>
        )}
        <td className="date">
          <Date.Earliest value={entity.dates} />
        </td>
        {documentMode && (
          <td className="file-size">
            <FileSize value={entity.file_size}/>
          </td>
        )}
      </tr>
    );
  }
}

export default EntityTableRow;